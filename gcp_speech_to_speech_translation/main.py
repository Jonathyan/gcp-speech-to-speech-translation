import logging
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

# --- Best Practice: Use Python's logging module instead of print() ---
# This provides timestamps, log levels, and is more configurable.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = FastAPI()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Handles WebSocket connections for the echo service (Iteration 2).

    It accepts a connection, then enters a loop where it receives a JSON
    message and sends the exact same message back to the client.
    """
    await websocket.accept()
    client_id = f"{websocket.client.host}:{websocket.client.port}"
    logging.info(f"Client connected: {client_id}")
    try:
        while True:
            # --- Improvement: More specific error handling ---
            # This inner try/except handles errors with a single message
            # without disconnecting the client.
            try:
                data = await websocket.receive_json()
                logging.info(f"Received from {client_id}: {data}")
                await websocket.send_json(data)
                logging.info(f"Echoed to {client_id}: {data}")
            except ValueError:
                # This is raised by receive_json() if the data is not valid JSON.
                logging.warning(f"Invalid JSON received from {client_id}. Sending error.")
                await websocket.send_json({"error": "Invalid JSON format"})

    except WebSocketDisconnect:
        logging.info(f"Client disconnected: {client_id}")
    except Exception as e:
        # --- Improvement: Catch-all for unexpected errors ---
        # This ensures the server logs any other crashes within the connection.
        logging.error(f"An unexpected error occurred with {client_id}: {e}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
