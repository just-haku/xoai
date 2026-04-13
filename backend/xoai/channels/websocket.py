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

        while True:
            msg_data = await websocket.receive_json()
            user_text = msg_data.get("text")
            
            # Forward to supervisor
            # Note: process_message might return a stream generator
            response_stream = await process_message(user, user_text, conversation_id, channel="web")
            
            if hasattr(response_stream, "__aiter__"):
                async for chunk in response_stream:
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
