"""
Univac Aegis & Aviation Knowledge Tri-System Bridge
Architecture: Kommandogerat-58 Asynchronous Uplink
"""

import asyncio
import aiohttp
import logging
from datetime import datetime
from typing import Dict, Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | [KDO58 BRIDGE] | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

class TriSystemBridge:
    def __init__(self, aegis_url: str, aviation_url: str, node_id: str = "KDO58-Director-Alpha"):
        self.aegis_url = aegis_url
        self.aviation_url = aviation_url
        self.node_id = node_id
        self.session = None

    async def initialize(self):
        """Initializes the persistent asynchronous HTTP session."""
        timeout = aiohttp.ClientTimeout(total=3.0)
        self.session = aiohttp.ClientSession(timeout=timeout)
        logger.info(f"Bridge initialized for {self.node_id}.")
        logger.info(f"Aegis Target: {self.aegis_url}")
        logger.info(f"Aviation Target: {self.aviation_url}")

    async def shutdown(self):
        """Gracefully closes the network sockets."""
        if self.session:
            await self.session.close()
            logger.info("Bridge sockets closed.")

    async def dispatch_to_aegis(self, target_data: Dict[str, Any]):
        """
        Translates Kdo58 surface/air tracking data into the Univac Aegis Payload Schema
        and dispatches it to the Aegis Combat System ingestion node.
        """
        if not self.session:
            return

        aegis_payload = {
            "EventId": f"TRK-{int(datetime.utcnow().timestamp())}",
            "Timestamp": datetime.utcnow().isoformat() + "Z",
            "SourceNode": self.node_id,
            "EventType": "RADAR_TRACK_UPDATE",
            "SeverityLevel": target_data.get("threat_level", 0),
            "RawProtocolData": f"AZ:{target_data.get('azimuth')}|EL:{target_data.get('elevation')}|RNG:{target_data.get('range')}"
        }

        headers = {"X-Aegis-Client": self.node_id, "Content-Type": "application/json"}

        try:
            async with self.session.post(self.aegis_url, json=aegis_payload, headers=headers) as response:
                if response.status == 200:
                    logger.info(f"Aegis Uplink Successful: Track {aegis_payload['EventId']}")
                else:
                    logger.warning(f"Aegis Uplink Rejected: Status {response.status}")
        except Exception as e:
            logger.error(f"Aegis Uplink Fault: {str(e)}")

    async def dispatch_to_aviation(self, flight_telemetry: Dict[str, Any]):
        """
        Translates Kdo58 aerodynamic parameters into the Basic-Aviation-Knowledge Schema
        and dispatches it for flight logging and aerodynamic analysis.
        """
        if not self.session:
            return

        aviation_payload = {
            "TelemetryID": f"FLT-{int(datetime.utcnow().timestamp())}",
            "Timestamp": datetime.utcnow().isoformat() + "Z",
            "Airframe": flight_telemetry.get("target_class", "UNKNOWN_BOGEY"),
            "Kinematics": {
                "VelocityKnots": flight_telemetry.get("velocity_knots", 0.0),
                "AltitudeFeet": flight_telemetry.get("altitude_feet", 0.0),
                "Heading": flight_telemetry.get("heading", 0.0),
                "VerticalSpeed": flight_telemetry.get("v_speed", 0.0)
            }
        }

        headers = {"X-Aviation-Node": self.node_id, "Content-Type": "application/json"}

        try:
            async with self.session.post(self.aviation_url, json=aviation_payload, headers=headers) as response:
                if response.status in (200, 201):
                    logger.info(f"Aviation Downlink Successful: Telemetry {aviation_payload['TelemetryID']}")
                else:
                    logger.warning(f"Aviation Downlink Rejected: Status {response.status}")
        except Exception as e:
            logger.error(f"Aviation Downlink Fault: {str(e)}")

    async def broadcast_target_lock(self, kdo58_track: Dict[str, Any]):
        """
        Master method: Takes a raw Kdo58 track and simultaneously streams it to 
        both the Aegis weapon system and the Aviation knowledge base asynchronously.
        """
        task_aegis = asyncio.create_task(self.dispatch_to_aegis(kdo58_track))
        task_aviation = asyncio.create_task(self.dispatch_to_aviation(kdo58_track))
        
        await asyncio.gather(task_aegis, task_aviation)
