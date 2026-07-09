import asyncio
import os
import time
import sys

PORT = int(os.environ.get("PORT", "9100"))
BIND_ADDR = "0.0.0.0"
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/storage/printed_files")

os.makedirs(OUTPUT_DIR, exist_ok=True)

async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    addr = writer.get_extra_info('peername')
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Connection accepted from {addr}", flush=True)
    
    data = bytearray()
    try:
        while True:
            chunk = await reader.read(4096)
            if not chunk:
                break
            data.extend(chunk)
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Error reading from {addr}: {e}", file=sys.stderr, flush=True)
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass

    if data:
        timestamp = int(time.time())
        ext = "bin"
        if data.startswith(b"%PDF"):
            ext = "pdf"
        elif data.startswith(b"\x1b%-12345X"):
            ext = "pjl"
        elif data.startswith(b"\x1b@"):
            ext = "esc"
            
        filename = f"print_job_{timestamp}_{addr[0]}_{len(data)}.{ext}"
        filepath = os.path.join(OUTPUT_DIR, filename)
        try:
            with open(filepath, "wb") as f:
                f.write(data)
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Job saved: {filepath} ({len(data)} bytes)", flush=True)
        except Exception as e:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Failed to save job: {e}", file=sys.stderr, flush=True)

async def main():
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting TCP RAW 9100 printer server...", flush=True)
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Listening on {BIND_ADDR}:{PORT}", flush=True)
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Saving printed files to {OUTPUT_DIR}", flush=True)
    
    server = await asyncio.start_server(handle_client, BIND_ADDR, PORT)
    
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopping printer server...", flush=True)
