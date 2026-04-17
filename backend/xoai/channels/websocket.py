"""WebSocket router for real-time Web Portal chat."""

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from xoai.auth.dependencies import get_current_user_ws
from xoai.agents.supervisor import process_message

router = APIRouter()
logger = logging.getLogger("xoai.channels.websocket")


@router.websocket("/ws/chat")
async def chat_endpoint(websocket: WebSocket):
    """
    Real-time chat endpoint.
    Expects initial message to be an auth token or handled via dependency.
    """
    await websocket.accept()
    
    # Auth handshake
    try:
        data = await websocket.receive_json()
        token = data.get("token")
        user = await get_current_user_ws(token)
        if not user:
            await websocket.close(code=1008)
            return

        conversation_id = data.get("conversation_id", "default")
        
        logger.info(f"WebSocket connected: {user['id']}")

        active_agent = None

        while True:
            msg_data = await websocket.receive_json()
            m_type = msg_data.get("type")
            
            if m_type == "input_response":
                if active_agent and hasattr(active_agent, "input_event"):
                    active_agent.last_input_response = msg_data.get("response") # 'allow' or 'deny'
                    active_agent.input_event.set()
                continue
            if m_type == "abort":
                await websocket.send_json({"type": "generation_stopped"})
                continue

            user_text = msg_data.get("text")
            if not user_text:
                await websocket.send_json({"type": "error", "message": "Message text is required."})
                continue
            
            # Forward to supervisor
            # Note: We need a way to get the agent instance back or manage it here.
            # Simplified for Phase 4: process_message returns a stream.
            # We'll need a way for the stream to hold the agent reference.
            
            response_stream = await process_message(user, user_text, conversation_id, channel="web")
            
            # In a more robust system, we would track the generator's internal agent.
            # For now, we'll use a globally accessible or session-bound 'active_agent' 
            # if we can extract it from the stream or supervisor.
            
            if hasattr(response_stream, "__aiter__"):
                async for chunk in response_stream:
                    # Capture the agent instance if yielded (new protocol)
                    if isinstance(chunk, dict) and chunk.get("type") == "agent_instance":
                        active_agent = chunk["instance"]
                        continue
                    await websocket.send_json(chunk)
            else:
                await websocket.send_json({"type": "content", "content": str(response_stream)})

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected.")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close()
        except:
            pass
