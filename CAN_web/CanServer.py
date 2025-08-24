#!/usr/bin/env python3
"""
Pi B (Server) - FastAPI 網站伺服器
接收 Pi A 的 CAN 資料並提供即時網頁儀表板
支援 WebSocket 即時更新和多使用者同時觀看
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any
import uvicorn
from contextlib import asynccontextmanager

# 設定 logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/pi/Desktop/RPI_Desktop/CAN_web/CanServer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 全域資料儲存
latest_can_data = {}
websocket_connections: List[WebSocket] = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 生命週期管理"""
    logger.info("FastAPI server starting up...")
    yield
    logger.info("FastAPI server shutting down...")

# 建立 FastAPI 應用
app = FastAPI(
    title="CAN Data Viewer",
    description="即時 CAN 資料儀表板",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 設定，允許所有來源（生產環境請調整）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    """WebSocket 連線管理器"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"New WebSocket connection. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")
    
    async def broadcast_data(self, data: dict):
        """廣播資料給所有連線的使用者"""
        if not self.active_connections:
            return
        
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception as e:
                logger.warning(f"Failed to send data to WebSocket: {e}")
                disconnected.append(connection)
        
        # 移除失效的連線
        for connection in disconnected:
            self.disconnect(connection)

manager = ConnectionManager()

@app.get("/health")
async def health_check():
    """健康檢查端點，供 Pi A 測試連線"""
    return {
        "status": "healthy", 
        "timestamp": datetime.now().isoformat(),
        "connected_clients": len(manager.active_connections)
    }

@app.post("/api/can-data")
async def receive_can_data(data: Dict[str, Any]):
    """接收來自 Pi A 的 CAN 資料"""
    global latest_can_data
    
    try:
        # 更新最新資料
        latest_can_data = data
        latest_can_data['server_received_time'] = datetime.now().isoformat()
        
        # 廣播給所有 WebSocket 客戶端
        await manager.broadcast_data({
            "type": "can_data_update",
            "data": latest_can_data
        })
        
        logger.debug("Received and broadcasted CAN data")
        return {"status": "success", "message": "Data received"}
        
    except Exception as e:
        logger.error(f"Error processing CAN data: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/latest-data")
async def get_latest_data():
    """獲取最新的 CAN 資料（RESTful API）"""
    if not latest_can_data:
        return {"status": "no_data", "message": "No data available yet"}
    
    return {
        "status": "success",
        "data": latest_can_data,
        "timestamp": datetime.now().isoformat()
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 端點，用於即時資料更新"""
    await manager.connect(websocket)
    
    try:
        # 傳送初始資料
        if latest_can_data:
            await websocket.send_json({
                "type": "initial_data",
                "data": latest_can_data
            })
        
        # 保持連線並處理客戶端訊息
        while True:
            try:
                message = await websocket.receive_text()
                # 可以處理來自前端的指令
                logger.debug(f"Received WebSocket message: {message}")
            except asyncio.TimeoutError:
                # 定期發送 ping 保持連線
                await websocket.send_json({"type": "ping"})
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """主儀表板頁面"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>CAN Data Dashboard</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { 
                font-family: Arial, sans-serif; 
                margin: 0; 
                padding: 20px; 
                background-color: #f5f5f5; 
            }
            .header { 
                text-align: center; 
                margin-bottom: 30px; 
                color: #333; 
            }
            .status { 
                text-align: center; 
                margin: 20px 0; 
                padding: 10px; 
                border-radius: 5px; 
            }
            .connected { background-color: #d4edda; color: #155724; }
            .disconnected { background-color: #f8d7da; color: #721c24; }
            .grid { 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); 
                gap: 20px; 
            }
            .card { 
                background: white; 
                border-radius: 10px; 
                padding: 20px; 
                box-shadow: 0 2px 5px rgba(0,0,0,0.1); 
            }
            .card h3 { 
                margin-top: 0; 
                color: #333; 
                border-bottom: 2px solid #007bff; 
                padding-bottom: 10px; 
            }
            .data-item { 
                margin: 10px 0; 
                padding: 5px 0; 
            }
            .label { 
                font-weight: bold; 
                color: #666; 
            }
            .value { 
                float: right; 
                color: #333; 
            }
            .timestamp { 
                font-size: 0.9em; 
                color: #999; 
                text-align: center; 
                margin-top: 20px; 
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🚗 CAN Data Dashboard</h1>
            <div id="status" class="status disconnected">等待資料連線...</div>
        </div>
        
        <div class="grid">
            <div class="card">
                <h3>🗺️ GPS 資訊</h3>
                <div id="gps-data">等待資料...</div>
            </div>
            
            <div class="card">
                <h3>🏃‍♂️ 速度資訊</h3>
                <div id="velocity-data">等待資料...</div>
            </div>
            
            <div class="card">
                <h3>🔋 電池狀態</h3>
                <div id="accumulator-data">等待資料...</div>
            </div>
            
            <div class="card">
                <h3>⚡ 逆變器狀態</h3>
                <div id="inverter-data">等待資料...</div>
            </div>
            
            <div class="card">
                <h3>🎮 VCU 控制</h3>
                <div id="vcu-data">等待資料...</div>
            </div>
            
            <div class="card">
                <h3>🧭 IMU 資訊</h3>
                <div id="imu-data">等待資料...</div>
            </div>
        </div>
        
        <div class="timestamp" id="last-update">最後更新: --</div>

        <script>
            let ws;
            let reconnectInterval = 5000;
            
            function connectWebSocket() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
                
                ws.onopen = function(event) {
                    console.log('WebSocket connected');
                    document.getElementById('status').textContent = '🟢 即時連線中';
                    document.getElementById('status').className = 'status connected';
                };
                
                ws.onmessage = function(event) {
                    const message = JSON.parse(event.data);
                    if (message.type === 'can_data_update' || message.type === 'initial_data') {
                        updateDashboard(message.data);
                    }
                };
                
                ws.onclose = function(event) {
                    console.log('WebSocket disconnected');
                    document.getElementById('status').textContent = '🔴 連線中斷，嘗試重連...';
                    document.getElementById('status').className = 'status disconnected';
                    setTimeout(connectWebSocket, reconnectInterval);
                };
                
                ws.onerror = function(error) {
                    console.error('WebSocket error:', error);
                };
            }
            
            function updateDashboard(data) {
                // 更新 GPS 資料
                const gpsHtml = `
                    <div class="data-item">
                        <span class="label">緯度:</span>
                        <span class="value">${data.gps?.lat || 'N/A'}</span>
                    </div>
                    <div class="data-item">
                        <span class="label">經度:</span>
                        <span class="value">${data.gps?.lon || 'N/A'}</span>
                    </div>
                    <div class="data-item">
                        <span class="label">海拔:</span>
                        <span class="value">${data.gps?.alt || 'N/A'} m</span>
                    </div>
                `;
                document.getElementById('gps-data').innerHTML = gpsHtml;
                
                // 更新速度資料
                const velocityHtml = `
                    <div class="data-item">
                        <span class="label">速度:</span>
                        <span class="value">${data.velocity?.speed_kmh?.toFixed(1) || 'N/A'} km/h</span>
                    </div>
                    <div class="data-item">
                        <span class="label">線性速度 X:</span>
                        <span class="value">${data.velocity?.linear_x?.toFixed(2) || 'N/A'} m/s</span>
                    </div>
                    <div class="data-item">
                        <span class="label">線性速度 Y:</span>
                        <span class="value">${data.velocity?.linear_y?.toFixed(2) || 'N/A'} m/s</span>
                    </div>
                `;
                document.getElementById('velocity-data').innerHTML = velocityHtml;
                
                // 更新電池資料
                const accumulatorHtml = `
                    <div class="data-item">
                        <span class="label">電量 (SOC):</span>
                        <span class="value">${data.accumulator?.soc || 'N/A'}%</span>
                    </div>
                    <div class="data-item">
                        <span class="label">電壓:</span>
                        <span class="value">${data.accumulator?.voltage?.toFixed(2) || 'N/A'} V</span>
                    </div>
                    <div class="data-item">
                        <span class="label">電流:</span>
                        <span class="value">${data.accumulator?.current?.toFixed(2) || 'N/A'} A</span>
                    </div>
                    <div class="data-item">
                        <span class="label">溫度:</span>
                        <span class="value">${data.accumulator?.temperature?.toFixed(1) || 'N/A'}°C</span>
                    </div>
                `;
                document.getElementById('accumulator-data').innerHTML = accumulatorHtml;
                
                // 更新逆變器資料
                let inverterHtml = '';
                if (data.inverters) {
                    Object.entries(data.inverters).forEach(([key, inv]) => {
                        inverterHtml += `
                            <div class="data-item">
                                <span class="label">${inv.name} 扭力:</span>
                                <span class="value">${inv.torque?.toFixed(2) || 'N/A'} Nm</span>
                            </div>
                            <div class="data-item">
                                <span class="label">${inv.name} 轉速:</span>
                                <span class="value">${inv.speed || 'N/A'} RPM</span>
                            </div>
                        `;
                    });
                }
                document.getElementById('inverter-data').innerHTML = inverterHtml || '無資料';
                
                // 更新 VCU 資料
                const vcuHtml = `
                    <div class="data-item">
                        <span class="label">方向盤:</span>
                        <span class="value">${data.vcu?.steer || 'N/A'}</span>
                    </div>
                    <div class="data-item">
                        <span class="label">油門:</span>
                        <span class="value">${data.vcu?.accel || 'N/A'}%</span>
                    </div>
                    <div class="data-item">
                        <span class="label">煞車:</span>
                        <span class="value">${data.vcu?.brake || 'N/A'}%</span>
                    </div>
                `;
                document.getElementById('vcu-data').innerHTML = vcuHtml;
                
                // 更新 IMU 資料
                const imuHtml = `
                    <div class="data-item">
                        <span class="label">Roll:</span>
                        <span class="value">${data.imu?.euler_angles?.roll?.toFixed(1) || 'N/A'}°</span>
                    </div>
                    <div class="data-item">
                        <span class="label">Pitch:</span>
                        <span class="value">${data.imu?.euler_angles?.pitch?.toFixed(1) || 'N/A'}°</span>
                    </div>
                    <div class="data-item">
                        <span class="label">Yaw:</span>
                        <span class="value">${data.imu?.euler_angles?.yaw?.toFixed(1) || 'N/A'}°</span>
                    </div>
                `;
                document.getElementById('imu-data').innerHTML = imuHtml;
                
                // 更新時間戳
                document.getElementById('last-update').textContent = 
                    `最後更新: ${new Date().toLocaleString()}`;
            }
            
            // 啟動 WebSocket 連線
            connectWebSocket();
        </script>
    </body>
    </html>
    """
    return html_content

if __name__ == "__main__":
    import os
    
    # 從環境變數讀取設定，或使用預設值
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 8000))
    
    logger.info(f"Starting FastAPI server on {host}:{port}")
    
    uvicorn.run(
        "CanServer:app", 
        host=host,
        port=port,
        reload=False,  # 生產環境設為 False
        access_log=True,
        log_level="info"
    )
