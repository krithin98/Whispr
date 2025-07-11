import asyncio
import json
import random
import time
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI(
    title="6-Week Whispr Co-pilot API",
    description="Real-Time Decision Copilot - Week 1 MVP",
    version="0.1.0"
)

# Store active WebSocket connections
active_connections: list[WebSocket] = []

class TickData:
    """Simulated tick data generator"""
    
    @staticmethod
    def generate_tick() -> Dict[str, Any]:
        """Generate a simulated tick with realistic trading data"""
        base_price = 4500.0  # SPX-like base
        price_change = random.uniform(-10, 10)
        current_price = base_price + price_change
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "symbol": "SPX",
            "price": round(current_price, 2),
            "volume": random.randint(1000, 50000),
            "bid": round(current_price - 0.1, 2),
            "ask": round(current_price + 0.1, 2),
            "change": round(price_change, 2),
            "change_percent": round((price_change / base_price) * 100, 3),
            "tick_id": int(time.time() * 1000)
        }

@app.get("/")
async def health_check():
    """Health check endpoint - Week 1 deliverable"""
    return JSONResponse({
        "status": "healthy",
        "service": "6-Week Whispr Co-pilot",
        "version": "0.1.0",
        "timestamp": datetime.utcnow().isoformat(),
        "active_connections": len(active_connections),
        "week": 1,
        "deliverable": "Data Engine & WebSocket"
    })

@app.websocket("/ws/ticks")
async def websocket_ticks(websocket: WebSocket):
    """WebSocket endpoint for streaming tick data - Week 1 deliverable"""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        # Send initial connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connection",
            "message": "Connected to tick stream",
            "timestamp": datetime.utcnow().isoformat()
        }))
        
        # Stream ticks every second
        while True:
            tick_data = TickData.generate_tick()
            await websocket.send_text(json.dumps({
                "type": "tick",
                "data": tick_data
            }))
            
            # Wait 1 second before next tick
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        print(f"WebSocket disconnected. Active connections: {len(active_connections)}")
    except Exception as e:
        print(f"WebSocket error: {e}")
        if websocket in active_connections:
            active_connections.remove(websocket)

@app.get("/api/status")
async def api_status():
    """Additional status endpoint for monitoring"""
    return {
        "active_connections": len(active_connections),
        "uptime": "running",
        "features": {
            "websocket_ticks": "active",
            "health_check": "active"
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True) 