"""Persistent controller for the Jingshi standing desk.

Wraps the BLE connection and the confirmed protocol (see protocol.py and
specs/reverse-engineer.md) behind a small async API meant to be held open for
the lifetime of a long-running service, rather than reconnecting per action.

Safety: the desk itself has no movement timeout (confirmed: a single UP/DOWN
command moves it indefinitely until an explicit STOP). To avoid a bug or a
crashed client leaving the desk moving forever, this controller auto-stops
any movement it starts after MAX_MOVE_SECONDS.
"""

import asyncio
import logging

from bleak import BleakClient, BleakScanner

import protocol

DEVICE_NAME = "BLE SPP"
WRITE_UUID = "0000fee2-0000-1000-8000-00805f9b34fb"
NOTIFY_UUID = "0000fee1-0000-1000-8000-00805f9b34fb"

MAX_MOVE_SECONDS = 20.0
IDLE_TIMEOUT_SECONDS = 1.0  # telemetry arrives ~every 250ms while moving

logger = logging.getLogger("desk_control.controller")


class DeskNotConnected(RuntimeError):
    pass


class Desk:
    def __init__(self):
        self._client: BleakClient | None = None
        self._height_cm: float | None = None
        self._is_moving = False
        self._watchdog_task: asyncio.Task | None = None
        self._idle_monitor_task: asyncio.Task | None = None
        self._notification_event = asyncio.Event()
        self._lock = asyncio.Lock()

    @property
    def height_cm(self) -> float | None:
        return self._height_cm

    @property
    def is_moving(self) -> bool:
        return self._is_moving

    @property
    def is_connected(self) -> bool:
        return self._client is not None and self._client.is_connected

    async def connect(self, timeout: float = 10.0) -> None:
        logger.info("Scanning for '%s'...", DEVICE_NAME)
        device = await BleakScanner.find_device_by_name(DEVICE_NAME, timeout=timeout)
        if device is None:
            raise DeskNotConnected(f"'{DEVICE_NAME}' not found")

        client = BleakClient(device, disconnected_callback=self._on_disconnected)
        await client.connect()
        await client.start_notify(NOTIFY_UUID, self._on_notification)
        self._client = client
        logger.info("Connected to desk at %s", device.address)

    async def disconnect(self) -> None:
        self._cancel_watchdog()
        self._cancel_idle_monitor()
        if self._client is not None:
            await self._client.disconnect()
            self._client = None

    def _on_disconnected(self, client: BleakClient) -> None:
        logger.warning("Desk disconnected")
        self._client = None
        self._is_moving = False
        self._cancel_watchdog()
        self._cancel_idle_monitor()

    def _on_notification(self, sender, data: bytearray) -> None:
        parsed = protocol.parse_notification(bytes(data))
        if parsed is None:
            logger.warning("Unrecognized notification: %s", bytes(data).hex(" "))
            return
        if not parsed["checksum_valid"]:
            logger.warning("Bad checksum on notification: %s", bytes(data).hex(" "))
            return
        self._height_cm = parsed["height_cm"]
        self._notification_event.set()

    async def _write(self, frame: bytes) -> None:
        if self._client is None or not self._client.is_connected:
            raise DeskNotConnected("Desk is not connected")
        await self._client.write_gatt_char(WRITE_UUID, frame, response=True)

    def _cancel_watchdog(self) -> None:
        if self._watchdog_task is not None:
            self._watchdog_task.cancel()
            self._watchdog_task = None

    def _arm_watchdog(self) -> None:
        self._cancel_watchdog()
        self._watchdog_task = asyncio.create_task(self._watchdog())

    async def _watchdog(self) -> None:
        try:
            await asyncio.sleep(MAX_MOVE_SECONDS)
            logger.warning(
                "Movement exceeded %.0fs without an explicit stop; auto-stopping",
                MAX_MOVE_SECONDS,
            )
            await self.stop()
        except asyncio.CancelledError:
            pass

    def _cancel_idle_monitor(self) -> None:
        if self._idle_monitor_task is not None:
            self._idle_monitor_task.cancel()
            self._idle_monitor_task = None

    def _arm_idle_monitor(self) -> None:
        self._cancel_idle_monitor()
        self._idle_monitor_task = asyncio.create_task(self._idle_monitor())

    async def _idle_monitor(self) -> None:
        """Declare movement finished once telemetry goes quiet (the desk only
        sends notifications while actually moving)."""
        try:
            while True:
                self._notification_event.clear()
                try:
                    await asyncio.wait_for(
                        self._notification_event.wait(), timeout=IDLE_TIMEOUT_SECONDS
                    )
                except asyncio.TimeoutError:
                    self._is_moving = False
                    self._cancel_watchdog()
                    return
        except asyncio.CancelledError:
            pass

    def _movement_started(self) -> None:
        self._is_moving = True
        self._arm_watchdog()
        self._arm_idle_monitor()

    async def move_up(self) -> None:
        async with self._lock:
            await self._write(protocol.UP_FRAME)
            self._movement_started()

    async def move_down(self) -> None:
        async with self._lock:
            await self._write(protocol.DOWN_FRAME)
            self._movement_started()

    async def stop(self) -> None:
        async with self._lock:
            await self._write(protocol.STOP_FRAME)
            self._is_moving = False
            self._cancel_watchdog()
            self._cancel_idle_monitor()

    async def move_to(self, height_cm: float) -> None:
        async with self._lock:
            await self._write(protocol.move_to_frame(height_cm))
            self._movement_started()

    async def refresh_height(self, timeout: float = 2.0) -> float | None:
        """Actively query the current height.

        The desk only reports height while moving, but sending STOP while
        already idle is a safe no-op that still triggers exactly one status
        notification -- use that as a way to read height on demand.
        """
        if self._is_moving:
            return self._height_cm

        async with self._lock:
            self._notification_event.clear()
            await self._write(protocol.STOP_FRAME)
            try:
                await asyncio.wait_for(self._notification_event.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                logger.warning("No notification received after height-refresh STOP")
        return self._height_cm
