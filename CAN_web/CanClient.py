#!/usr/bin/env python3
"""
Pi A (Client) - CAN 資料接收與傳送
讀取 CAN bus 資料，透過 HTTP POST 傳送給 Pi B
具備自動重連功能，不會因為 Pi B 離線而停止運行
"""

import asyncio
import aiohttp
import json
import time
import logging
from datetime import datetime
import can
from CanDecoder import CanDecoder

# 設定 logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/pi/can_client.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CANDataSender:
    def __init__(self, server_url="http://pi-b.tailscale:8000"):
        self.server_url = server_url
        self.decoder = CanDecoder()
        self.session = None
        self.can_bus = None
        self.is_connected = False
        self.last_send_time = 0
        self.send_interval = 0.1  # 每 100ms 送一次資料
        
    async def init_can_bus(self):
        """初始化 CAN bus 連線"""
        try:
            # 根據你的 CAN 介面調整 (can0, vcan0 等)
            self.can_bus = can.interface.Bus(
                channel='can0',
                bustype='socketcan',
                receive_own_messages=False
            )
            logger.info("CAN bus initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize CAN bus: {e}")
            return False
    
    async def init_http_session(self):
        """初始化 HTTP session"""
        timeout = aiohttp.ClientTimeout(total=5, connect=2)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=aiohttp.TCPConnector(limit=10)
        )
    
    async def test_server_connection(self):
        """測試與 Pi B 的連線"""
        try:
            async with self.session.get(f"{self.server_url}/health") as response:
                if response.status == 200:
                    self.is_connected = True
                    logger.info("Successfully connected to Pi B")
                    return True
        except Exception as e:
            self.is_connected = False
            logger.warning(f"Cannot connect to Pi B: {e}")
            return False
    
    async def send_data_to_server(self, data):
        """傳送資料到 Pi B"""
        if not self.is_connected:
            return False
            
        try:
            headers = {'Content-Type': 'application/json'}
            async with self.session.post(
                f"{self.server_url}/api/can-data", 
                json=data, 
                headers=headers
            ) as response:
                if response.status == 200:
                    return True
                else:
                    logger.warning(f"Server returned status {response.status}")
                    return False
        except Exception as e:
            logger.error(f"Failed to send data to server: {e}")
            self.is_connected = False
            return False
    
    async def process_can_messages(self):
        """處理 CAN 訊息的主要循環"""
        logger.info("Starting CAN message processing...")
        
        while True:
            try:
                # 非阻塞式讀取 CAN 訊息
                message = self.can_bus.recv(timeout=0.01)
                if message:
                    # 使用你的 CanDecoder 處理訊息
                    self.decoder.process_can_message(message)
                
                # 定期送資料到 Pi B
                current_time = time.time()
                if current_time - self.last_send_time > self.send_interval:
                    if self.is_connected:
                        # 收集所有資料
                        data_package = {
                            'timestamp': datetime.now().isoformat(),
                            'gps': self.decoder.data_store['gps'],
                            'velocity': self.decoder.data_store['velocity'],
                            'accumulator': self.decoder.data_store['accumulator'],
                            'inverters': self.decoder.data_store['inverters'],
                            'vcu': self.decoder.data_store['vcu'],
                            'imu': self.decoder.data_store['imu'],
                            'canlogging': self.decoder.data_store['canlogging']
                        }
                        
                        # 送到 Pi B
                        await self.send_data_to_server(data_package)
                    
                    self.last_send_time = current_time
                
                # 短暂等待避免 CPU 過載
                await asyncio.sleep(0.001)
                
            except Exception as e:
                logger.error(f"Error in CAN processing: {e}")
                await asyncio.sleep(1)
    
    async def connection_monitor(self):
        """監控與 Pi B 的連線狀態"""
        while True:
            if not self.is_connected:
                logger.info("Attempting to connect to Pi B...")
                await self.test_server_connection()
                
                if self.is_connected:
                    logger.info("Connected to Pi B successfully!")
                else:
                    logger.info("Pi B not available, retrying in 5 seconds...")
                    await asyncio.sleep(5)
            else:
                # 每 30 秒檢查一次連線
                await asyncio.sleep(30)
                await self.test_server_connection()
    
    async def run(self):
        """主程式運行"""
        logger.info("Starting CAN Data Sender...")
        
        # 初始化 CAN bus
        if not await self.init_can_bus():
            logger.error("Failed to initialize CAN bus, exiting...")
            return
        
        # 初始化 HTTP session
        await self.init_http_session()
        
        try:
            # 同時運行 CAN 處理和連線監控
            await asyncio.gather(
                self.process_can_messages(),
                self.connection_monitor()
            )
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            if self.session:
                await self.session.close()
            if self.can_bus:
                self.can_bus.shutdown()

async def main():
    # 可以透過環境變數或設定檔調整 server URL
    import os
    # server_url = os.getenv('PI_B_URL', 'http://pi-b.tailscale:8000')
    server_url = "http://localhost:8000"
    sender = CANDataSender(server_url)
    await sender.run()

if __name__ == "__main__":
    asyncio.run(main())
