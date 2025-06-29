from fastapi import FastAPI, WebSocket
import asyncio

app = FastAPI(title="Seer-MVP")

@app.get("/")
async def root():
    return {"status": "OK", "message": "Seer backend running"}

@app.websocket("/ws/ticks")
async def websocket_ticks(ws: WebSocket):
    await ws.accept()
    tick = 0
    while True:
        await ws.send_json({"tick": tick, "value": 100 + tick})
        await asyncio.sleep(1)        # 1-Hz simulated stream
        tick += 1 