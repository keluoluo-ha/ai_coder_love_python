import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.agent.support_agent import SupportAgent


router = APIRouter()


@router.get("/ai/manus/chat")
async def chat_stream(message: str, chatId: str = None, runId: str = None, replyType: str = None):
    agent = SupportAgent()

    async def event_generator():
        # 遍历 run_stream 产出的事件，逐条转成 SSE 推给前端
        async for ev in agent.run_stream(message):
            if ev["type"] == "text":
                yield f"data: {ev['content']}\n\n"
            elif ev["type"] == "ask_human":
                ask_event = {"runId": runId or "r1", "chatId": chatId, **ev["data"]}
                yield f"event: ask_human\ndata: {json.dumps(ask_event, ensure_ascii=False)}\n\n"
            elif ev["type"] == "done":
                yield f"event: done\ndata: {json.dumps({'status': 'FINISHED'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
