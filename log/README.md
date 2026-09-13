# Capture logs

`.pklg` files captured with macOS PacketLogger go here for local analysis with
`pklg_decode.py`. They're gitignored on purpose: a Bluetooth HCI capture
records *all* nearby Bluetooth traffic, not just the desk, including your
Mac's own Bluetooth address and the names/addresses of other devices around
you (headphones, lights, TVs, etc.). Keep captures local.

The findings already extracted from past captures are written up in
`specs/reverse-engineer.md`.

## How to capture

macOS won't record Bluetooth HCI traffic by default, so there are two
one-time setup steps before you can capture anything.

1. **Install PacketLogger.** It's not part of Xcode itself -- it ships in the
   separate "Additional Tools for Xcode" package:
   - Go to `developer.apple.com/download/all/` (sign in with your Apple ID)
   - Search for "Additional Tools for Xcode", matching your Xcode version
     (check with `xcodebuild -version`)
   - Open the downloaded `.dmg` and drag `PacketLogger.app` (in the
     `Hardware/` folder) into `/Applications`

2. **Install the Bluetooth logging profile.** As of macOS 14.5+, PacketLogger
   won't capture anything until this is installed (the old
   Option+Shift-click "Debug" menu on the Bluetooth menu bar icon was
   removed):
   - Go to
     `developer.apple.com/bug-reporting/profiles-and-logs/?platform=macos&name=bluetooth`
   - Download and install the Bluetooth profile (System Settings -> General
     -> VPN & Device Management, or double-click the download)
   - **Reboot** -- the profile only takes effect after a restart

Then, to capture:

1. Open PacketLogger and click **Start**.
2. Connect to the desk with whatever app/tool you're testing (disconnect it
   first if already connected -- the desk usually only accepts one BLE
   connection at a time).
3. Perform the action you want to capture. Isolate one action per capture
   where possible (e.g. only press UP, nothing else) -- much easier to read
   than a capture with several actions mixed together.
4. For anything that stops movement, stay connected and idle for several
   seconds *before* stopping the capture, so you can see the telemetry go
   quiet and confirm it actually stopped, not just that a command was sent.
5. Stop the capture and save it as a `.pklg` file in this folder.
6. Decode it: `python3 pklg_decode.py log/your-capture.pklg`
