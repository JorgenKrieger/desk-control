# Capture logs

`.pklg` files captured with macOS PacketLogger go here for local analysis with
`pklg_decode.py`. They're gitignored on purpose: a Bluetooth HCI capture
records *all* nearby Bluetooth traffic, not just the desk, including your
Mac's own Bluetooth address and the names/addresses of other devices around
you (headphones, lights, TVs, etc.). Keep captures local.

The findings already extracted from past captures are written up in
`specs/reverse-engineer.md`.
