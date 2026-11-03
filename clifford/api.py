import asyncio
import json
import time
from collections import deque
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, text

from .config import Settings
from .contracts import (
    ApprovalResponse,
    Chat,
    ChatResponse,
    Decision,
    Event,
    MemoryInput,
    MemoryResponse,
    PlanInput,
    PlanRequest,
    SessionDetail,
    SessionResponse,
    TaskResponse,
    ToolCall,
    ToolResponse,
    uid,
)
from .engine import Engine
from .persistence import Approval, Audit, Memory, Message, Session, Store, Task, User, record
from .platforms import Platforms
from .providers.llm import OllamaProvider, ProviderError, Router
from .providers.speech import LocalSpeech
from .tools import Registry, ToolError
from .transport import require_socket
from .voice_tickets import VoiceTickets


def create_app(settings=None, provider=None):
    settings = settings or Settings()
    store = Store(settings.database_url)
    registry = Registry(settings, store)
    engine = Engine(settings, store, provider or Router(settings), registry)
    hits = deque()
    speech = LocalSpeech(settings)
    platforms = Platforms(settings, registry)
    voice_tickets = VoiceTickets()

    @asynccontextmanager
    async def lifespan(app):
        # Fail clearly on an unmigrated database. Never silently create a production schema.
        with store.db() as db:
            db.execute(text("SELECT version_num FROM alembic_version"))
            if not db.get(User, settings.clifford_user_id):
                db.add(User(id=settings.clifford_user_id))
        yield
        store.engine.dispose()

    app = FastAPI(
        title="Clifford",
        version="0.1.0",
        lifespan=lifespan,
        description="Private Unix-socket kernel. One configured identity; no shared access token.",
    )
    app.state.store, app.state.engine, app.state.registry = store, engine, registry

    def identify(scope):
        require_socket(scope, settings.socket_path)
        cutoff = time.monotonic() - 60
        while hits and hits[0] < cutoff:
            hits.popleft()
        if len(hits) >= settings.requests_per_minute:
            raise HTTPException(429, detail={"code": "rate_limited"})
        hits.append(time.monotonic())
        return settings.clifford_user_id

    async def identity(request: Request):
        return identify(request.scope)

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        try:
            require_socket(request.scope, settings.socket_path)
        except HTTPException:
            return JSONResponse(
                status_code=403, content={"error": {"code": "private_socket_required"}}
            )
        correlation = uid()
        # Reject oversized JSON before parsing. Streaming uploads aren't supported.
        if request.method in {"POST", "PUT", "PATCH"}:
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > 128000:
                    return JSONResponse(
                        status_code=413, content={"error": {"code": "body_too_large"}}
                    )
            request._body = bytes(body)
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.exception_handler(ProviderError)
    async def provider_error(request, exc):
        return JSONResponse(status_code=503, content={"error": {"code": exc.code}})

    @app.exception_handler(ToolError)
    async def tool_error(request, exc):
        return JSONResponse(status_code=400, content={"error": {"code": str(exc)}})

    from fastapi.exceptions import RequestValidationError

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # Pydantic error inputs can include sensitive text. Do not echo them.
        return JSONResponse(status_code=422, content={"error": {"code": "invalid_request"}})

    @app.get("/v1/health")
    def health():
        with store.db() as db:
            db.execute(text("SELECT 1"))
        return {"status": "ok", "version": "0.1.0"}

    @app.get("/v1/providers")
    def providers(owner=Depends(identity)):
        return {
            "selected": "ollama",
            "model": settings.default_llm_model,
            "requires_model_api_key": False,
            "assistant_name": settings.assistant_name,
            "wake_phrase": settings.wake_phrase,
            "speech": {
                "recognition": "vosk",
                "model_installed": speech.available(),
                "output": "device_local_speech",
            },
            "capabilities": ["text_generation", "streaming", "usage_reporting"],
            "unavailable": ["email", "native_phone_app", "native_watch_app"],
        }

    @app.get("/v1/providers/check")
    async def provider_check(owner=Depends(identity)):
        return await OllamaProvider(settings).check()

    @app.get("/v1/platforms")
    def platform_list(owner=Depends(identity)):
        return platforms.list()

    @app.post("/v1/platforms/{name}/connect")
    async def platform_connect(name: str, owner=Depends(identity)):
        return await platforms.connect(name)

    @app.post("/v1/platforms/{name}/disconnect")
    def platform_disconnect(name: str, owner=Depends(identity)):
        return platforms.disconnect(name)

    @app.post("/v1/chat", response_model=ChatResponse)
    async def chat(body: Chat, owner=Depends(identity)):
        session_id = engine.session(owner, body.session_id)
        events = [event async for event in engine.chat(owner, body, session_id)]
        return {"session_id": session_id, "events": events}

    @app.post("/v1/chat/stream", responses={200: {"content": {"text/event-stream": {}}}})
    async def stream_chat(body: Chat, request: Request, owner=Depends(identity)):
        session_id = engine.session(owner, body.session_id)

        async def stream():
            async for event in engine.chat(owner, body, session_id):
                if await request.is_disconnected():
                    break
                yield f"id: {event.id}\nevent: {event.type}\ndata: {event.model_dump_json()}\n\n"

        return StreamingResponse(
            stream(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no"}
        )

    @app.get("/v1/sessions", response_model=list[SessionResponse])
    def sessions(owner=Depends(identity)):
        with store.db() as db:
            return [
                record(s)
                for s in db.scalars(
                    select(Session)
                    .where(Session.owner == owner)
                    .order_by(Session.created_at.desc())
                    .limit(100)
                )
            ]

    @app.get("/v1/sessions/{session_id}", response_model=SessionDetail)
    def session_detail(session_id: str, owner=Depends(identity)):
        engine.session(owner, session_id)
        with store.db() as db:
            return {
                "id": session_id,
                "messages": [
                    record(m)
                    for m in db.scalars(
                        select(Message)
                        .where(Message.session_id == session_id)
                        .order_by(Message.created_at)
                        .limit(1000)
                    )
                ],
            }

    @app.get("/v1/memory", response_model=list[MemoryResponse])
    def memories(
        q: str = Query("", max_length=500),
        scope: str | None = None,
        category: str | None = None,
        owner=Depends(identity),
    ):
        return engine.memories(owner, q, scope, category)

    @app.post("/v1/memory", status_code=201, response_model=MemoryResponse)
    def remember(body: MemoryInput, owner=Depends(identity)):
        with store.db() as db:
            memory = Memory(owner=owner, **body.model_dump())
            db.add(memory)
            db.flush()
            db.add(Audit(owner=owner, action="memory.created", resource_id=memory.id))
            return record(memory)

    @app.put("/v1/memory/{memory_id}", response_model=MemoryResponse)
    def update_memory(memory_id: str, body: MemoryInput, owner=Depends(identity)):
        with store.db() as db:
            memory = db.get(Memory, memory_id)
            if not memory or memory.owner != owner:
                raise HTTPException(404)
            for key, value in body.model_dump().items():
                setattr(memory, key, value)
            db.flush()
            db.add(Audit(owner=owner, action="memory.updated", resource_id=memory_id))
            return record(memory)

    @app.delete("/v1/memory/{memory_id}", status_code=204)
    def forget(memory_id: str, owner=Depends(identity)):
        with store.db() as db:
            memory = db.get(Memory, memory_id)
            if not memory or memory.owner != owner:
                raise HTTPException(404)
            db.delete(memory)
            db.add(Audit(owner=owner, action="memory.deleted", resource_id=memory_id))
        return Response(status_code=204)

    @app.get("/v1/tools")
    def tools(owner=Depends(identity)):
        return [tool.describe() for tool in registry.tools.values()]

    @app.post("/v1/tools/execute", response_model=ToolResponse, response_model_exclude_none=True)
    async def execute(body: ToolCall, owner=Depends(identity)):
        return await registry.execute(owner, body.tool, body.arguments)

    @app.get("/v1/approvals", response_model=list[ApprovalResponse])
    def approvals(owner=Depends(identity)):
        with store.db() as db:
            return [
                record(a)
                for a in db.scalars(
                    select(Approval)
                    .where(Approval.owner == owner)
                    .order_by(Approval.created_at.desc())
                    .limit(100)
                )
            ]

    @app.post(
        "/v1/approvals/{approval_id}/decision",
        response_model=ToolResponse,
        response_model_exclude_none=True,
    )
    async def decide(approval_id: str, body: Decision, owner=Depends(identity)):
        return await registry.decision(owner, approval_id, body.approve)

    @app.post("/v1/tasks", status_code=201, response_model=TaskResponse)
    def create_task(body: PlanInput, owner=Depends(identity)):
        return engine.create_plan(owner, body)

    @app.post("/v1/plans/propose", response_model=TaskResponse)
    async def propose(body: PlanRequest, owner=Depends(identity)):
        return await engine.propose_plan(owner, body)

    @app.get("/v1/tasks", response_model=list[TaskResponse])
    def tasks(owner=Depends(identity)):
        with store.db() as db:
            return [
                record(t)
                for t in db.scalars(
                    select(Task)
                    .where(Task.owner == owner)
                    .order_by(Task.created_at.desc())
                    .limit(100)
                )
            ]

    @app.get("/v1/tasks/{task_id}", response_model=TaskResponse)
    def task_detail(task_id: str, owner=Depends(identity)):
        with store.db() as db:
            task = db.get(Task, task_id)
            if not task or task.owner != owner:
                raise HTTPException(404)
            return record(task)

    @app.post("/v1/tasks/{task_id}/run", response_model=TaskResponse)
    async def run(task_id: str, owner=Depends(identity)):
        return await engine.run_plan(owner, task_id)

    @app.post("/v1/tasks/{task_id}/cancel", response_model=TaskResponse)
    def cancel(task_id: str, owner=Depends(identity)):
        with store.db() as db:
            task = db.get(Task, task_id)
            if not task or task.owner != owner:
                raise HTTPException(404)
            if task.status in {"completed", "failed"}:
                raise HTTPException(409)
            task.status = "cancelled"
            # Outstanding authorizations must not execute after cancellation.
            for approval in db.scalars(
                select(Approval).where(Approval.task_id == task_id, Approval.status == "pending")
            ):
                approval.status = "denied"
            return record(task)

    @app.post("/v1/voice/tickets")
    def voice_ticket(owner=Depends(identity)):
        return voice_tickets.issue(owner)

    @app.websocket("/v1/voice/listen")
    async def listen(ws: WebSocket):
        try:
            require_socket(ws.scope, settings.socket_path)
        except HTTPException:
            await ws.close(code=1008)
            return
        await ws.accept()
        correlation = uid()

        async def send(kind, **payload):
            event = Event(type=kind, correlation_id=correlation, payload=payload)
            await ws.send_json(json.loads(event.model_dump_json()))

        try:
            auth = await asyncio.wait_for(ws.receive_json(), 10)
            voice_tickets.consume(auth.get("ticket"))
            recognizer = await asyncio.to_thread(speech.recognizer)
            await send("audio.ready", sample_rate=16000, encoding="pcm_s16le", channels=1)
            window, received = time.monotonic(), 0
            while True:
                audio = await ws.receive_bytes()
                if len(audio) > 16000 or len(audio) % 2:
                    await send("error", code="invalid_audio_frame")
                    break
                if time.monotonic() - window > 10:
                    window, received = time.monotonic(), 0
                received += len(audio)
                if received > 640000:
                    await send("error", code="audio_rate_limit")
                    break
                transcript = await asyncio.to_thread(speech.accept, recognizer, audio)
                if transcript["text"]:
                    await send("audio.transcript", **transcript)
        except ProviderError as exc:
            await send("error", code=exc.code)
        except (HTTPException, ValueError, AttributeError, asyncio.TimeoutError):
            await send("error", code="voice_authentication_or_protocol_error")
        except WebSocketDisconnect:
            return
        finally:
            try:
                await ws.close()
            except RuntimeError:
                pass

    @app.websocket("/v1/realtime")
    async def realtime(ws: WebSocket):
        await ws.accept()
        try:
            owner = identify(ws.scope)
        except HTTPException:
            await ws.close(code=1008)
            return
        active = None
        correlation = uid()

        async def control(kind, **payload):
            event = Event(type=kind, correlation_id=correlation, payload=payload)
            await ws.send_json(json.loads(event.model_dump_json()))

        async def reply(body):
            try:
                sid = engine.session(owner, body.session_id)
                async for event in engine.chat(owner, body, sid):
                    await ws.send_json(json.loads(event.model_dump_json()))
            except ToolError as exc:
                await control("error", code=str(exc))

        try:
            while True:
                payload = await ws.receive_json()
                if payload.get("type") == "cancel":
                    if active and not active.done():
                        active.cancel()
                        await asyncio.gather(active, return_exceptions=True)
                    await control("task.cancelled")
                else:
                    try:
                        body = Chat.model_validate(payload)
                    except ValueError:
                        await ws.send_json(
                            {"type": "error", "payload": {"code": "invalid_request"}}
                        )
                        continue
                    if active and not active.done():
                        await control("error", code="session_busy")
                    else:
                        identify(ws.scope)  # shared rate budget
                        active = asyncio.create_task(reply(body))
        except (WebSocketDisconnect, ValueError, HTTPException):
            pass
        finally:
            if active and not active.done():
                active.cancel()
                await asyncio.gather(active, return_exceptions=True)

    if settings.web_root:
        app.mount(
            "/console",
            StaticFiles(directory=settings.web_root, html=True),
            name="console",
        )
    return app


app = create_app()
