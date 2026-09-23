import json
import uuid
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.agent.support_agent import SupportAgent
from app.agent.run_state_store import run_state_store


router = APIRouter()


class ManusReplyRequest(BaseModel):
    run_id: str = Field(alias="runId", min_length=1)
    answer: str = Field(min_length=1)
    chat_id: str | None = Field(default=None, alias="chatId")


@router.get("/ai/manus/chat")
async def chat_stream(message: str, chatId: str = None, runId: str = None, replyType: str = None):
    agent = SupportAgent()
    run_id = runId or str(uuid.uuid4())

    async def event_generator():
        # 遍历 run_stream 产出的事件，逐条转成 SSE 推给前端
        async for ev in agent.run_stream(message, run_id=run_id, chat_id=chatId):
            if ev["type"] == "text":
                yield f"data: {ev['content']}\n\n"
            elif ev["type"] == "ask_human":
                ask_event = {"runId": run_id, "chatId": chatId, **ev["data"]}
                yield f"event: ask_human\ndata: {json.dumps(ask_event, ensure_ascii=False)}\n\n"
            elif ev["type"] == "done":
                yield f"event: done\ndata: {json.dumps({'status': 'FINISHED'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/ai/manus/reply")
async def reply(request: ManusReplyRequest):
    if run_state_store.get(request.run_id) is None:
        raise HTTPException(status_code=404, detail="runId不存在或已过期")
    agent = SupportAgent()

    async def event_generator():
        try:
            async for event in agent.resume_with_human_reply(request.run_id, request.answer, request.chat_id):
                if event["type"] == "text":
                    yield f"data: {event['content']}\n\n"
                elif event["type"] == "ask_human":
                    payload = {"runId": request.run_id, "chatId": request.chat_id, **event["data"]}
                    yield f"event: ask_human\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                elif event["type"] == "done":
                    yield f"event: done\ndata: {json.dumps({'status': 'WAITING' if run_state_store.get(request.run_id) else 'FINISHED'})}\n\n"
        except (LookupError, ValueError) as exc:
            yield f"event: error\ndata: {json.dumps({'detail': str(exc)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
