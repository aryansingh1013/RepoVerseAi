import time
from typing import Dict, Any
from backend.mcp.interfaces import IMCPServer

class HealthStatusChecker:
    @staticmethod
    def check_server_health(server: IMCPServer) -> Dict[str, Any]:
        """
        Executes server health checks and records latency telemetry.
        """
        start = time.perf_counter()
        try:
            telemetry = server.health()
            latency = (time.perf_counter() - start) * 1000.0
            
            # Inject latency and verify keys
            telemetry["latency_ms"] = round(latency, 2)
            if "status" not in telemetry:
                telemetry["status"] = "healthy"
                
            return telemetry
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000.0
            return {
                "status": "unhealthy",
                "latency_ms": round(latency, 2),
                "errors": [f"Health check failed with error: {str(e)}"]
            }
