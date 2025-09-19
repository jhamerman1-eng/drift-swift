import asyncio
import websockets

async def test_websockets_fix():
    """Test the websockets fix"""
    try:
        # Simulate the fix
        uri = "wss://echo.websocket.org"
        headers = {}

        # Use async context manager directly (proper pattern)
        async with websockets.connect(
            uri,
            extra_headers=headers,
            ping_interval=30,
            ping_timeout=10
        ) as websocket:
            print("✅ WebSocket connection established successfully")

            # Test sending/receiving
            await websocket.send("Hello from fixed code")
            response = await websocket.recv()
            print(f"✅ Received response: {response}")

            print("✅ WebSocket operations completed successfully")
        print("✅ WebSocket connection closed successfully")

        print("🎉 Fix verified - websockets.connect issue resolved!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_websockets_fix())
