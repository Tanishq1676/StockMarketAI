"""Quick WebSocket feed test using the `websockets` package."""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.getcwd(), "backend"))


async def main():
    import websockets

    try:
        async with websockets.connect("ws://127.0.0.1:8000/api/ws/market-updates") as ws:
            msg = await asyncio.wait_for(ws.recv(), timeout=30)
            data = json.loads(msg)
            print("WS message:", data["type"], "indices:", len(data["indices"]), "gainers:", len(data["top_gainers"]), "timestamp:", data["timestamp"][:19])
    except Exception as exc:
        print("WS FAILED:", exc)


if __name__ == "__main__":
    asyncio.run(main())
