from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json

router = APIRouter()


# Minimal MCP-like websocket: list tools + echo tool
@router.websocket("/ws/mcp/{agent_id}")
async def mcp_socket(websocket: WebSocket, agent_id: str):
    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            method = msg.get("method")
            id_ = msg.get("id")
            if method == "tools/list":
                tools = [
                    {
                        "name": "invoke",
                        "description": "Echo invoke",
                        "input": {"type": "object"},
                    },
                    {
                        "name": "list_runs",
                        "description": "List recent runs",
                        "input": {"type": "object"},
                    },
                ]
                await websocket.send_text(json.dumps({"id": id_, "result": tools}))
            elif method == "tools/call":
                params = msg.get("params", {})
                tool = params.get("tool")
                input_ = params.get("input")
                # For PoC, just echo
                await websocket.send_text(
                    json.dumps(
                        {
                            "id": id_,
                            "result": {
                                "tool": tool,
                                "agent_id": agent_id,
                                "echo": input_,
                            },
                        }
                    )
                )
            else:
                await websocket.send_text(
                    json.dumps({"id": id_, "error": {"message": "unknown method"}})
                )
    except WebSocketDisconnect:
        return
