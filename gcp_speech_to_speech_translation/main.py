import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Handles WebSocket connections for Iteration 1.

    It accepts a connection, prints a confirmation message, and then waits
    in a loop to keep the connection open. It handles disconnection gracefully.
    """
    await websocket.accept()
    print("Client connected")
    try:
        while True:
            # We must wait for messages to keep the connection alive.
            await websocket.receive_text()
    except WebSocketDisconnect:
        print("Client disconnected")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
