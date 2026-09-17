import json
import logging
from typing import Dict, Any, List, Callable, Awaitable
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class MCPEventBus:
    """
    Model Context Protocol (MCP) JSON-RPC Event Router for Event-Driven CRM Orchestration.
    """
    def __init__(self):
        self._handlers: Dict[str, List[Callable[[Dict[str, Any]], Awaitable[None]]]] = {}
        self._event_log: List[Dict[str, Any]] = []

    def subscribe(self, event_type: str, handler: Callable[[Dict[str, Any]], Awaitable[None]]):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    async def publish(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Publishes an MCP JSON-RPC formatted event.
        """
        mcp_event = {
            "jsonrpc": "2.0",
            "method": f"mcp/{event_type}",
            "params": {
                "event_type": event_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": payload
            }
        }
        
        self._event_log.append(mcp_event)
        logger.info(f"MCP Event Published: {event_type} | Params: {payload.get('lead_id')}")

        handlers = self._handlers.get(event_type, [])
        for handler in handlers:
            try:
                await handler(payload)
            except Exception as e:
                logger.error(f"Error executing MCP handler for {event_type}: {e}")

        return mcp_event

    def get_event_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._event_log[-limit:]

# Global singleton instance for app-wide event routing
mcp_event_bus = MCPEventBus()
