#!/usr/bin/env python3
"""Serve patched firmware for Wiz bulb OTA update.

Serves on port 80 (requires sudo). The bulb requests:
  GET /firmwares/ESP24_SHRGB_01/<version>/wizlight.bin?mac=...&fw=...

Any request for wizlight.bin will serve the patched firmware file.
"""

import http.server
import os
import sys


def resolve_firmware_path(arg):
    """Resolve firmware path: try as-is first, then relative to script dir."""
    if os.path.isabs(arg) or os.path.exists(arg):
        return os.path.abspath(arg)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, arg)


class OTAHandler(http.server.BaseHTTPRequestHandler):
    request_count = 0

    def do_GET(self):
        OTAHandler.request_count += 1
        req_num = OTAHandler.request_count
        print(f"\n>>> [{req_num}] {self.requestline}")
        print(f"    Headers: {dict(self.headers)}")

        if "wizlight.bin" in self.path:
            # Bait-and-switch mode: if two files given, serve second (patched) on
            # the FIRST completed transfer, first (original) on retries
            if len(sys.argv) > 2:
                if req_num == 1:
                    firmware_file = resolve_firmware_path(sys.argv[2])
                    print(f"    SWITCH: serving patched FIRST (request #{req_num})")
                else:
                    firmware_file = resolve_firmware_path(sys.argv[1])
                    print(f"    BAIT: serving original on retry (request #{req_num})")
            else:
                firmware_file = resolve_firmware_path(sys.argv[1] if len(sys.argv) > 1 else "ESP24_SHRGB_01_1.36.1.patched.bin")

            if not os.path.exists(firmware_file):
                print(f"    ERROR: {firmware_file} not found!")
                self.send_error(404)
                return

            size = os.path.getsize(firmware_file)
            print(f"    Serving {firmware_file} ({size} bytes)")

            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(size))
            self.end_headers()

            try:
                with open(firmware_file, "rb") as f:
                    self.wfile.write(f.read())
                print(f"    Done sending {size} bytes")
            except BrokenPipeError:
                print(f"    Bulb disconnected mid-download (request #{req_num})")
        else:
            print(f"    404 — not a firmware request")
            self.send_error(404)


if __name__ == "__main__":
    port = 80
    fw = sys.argv[1] if len(sys.argv) > 1 else "ESP24_SHRGB_01_1.36.1.patched.bin"
    firmware_file = resolve_firmware_path(fw)
    print(f"Serving {firmware_file} on port {port}")
    print(f"Waiting for bulb to request firmware...")
    print(f"The bulb will request: GET /firmwares/ESP24_SHRGB_01/*/wizlight.bin")
    print()

    server = http.server.HTTPServer(("", port), OTAHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
