import asyncio
import json
import time
from importlib.resources import files

from sqlalchemy import or_, select

from .contracts import Event, PlanInput, now, uid
from .persistence import Memory, Message, Session, Task, record
from .providers.llm import ProviderError
from .tools import ToolError


class Engine:
    def __init__(self, settings, store, provider, registry):
        self.settings, self.store, self.provider, self.registry = (
            settings,
            store,
            provider,
            registry,
        )
        self.system = (
            files("clifford").joinpath("prompts/system.md").read_text()
            + f"\nYour name is {settings.assistant_name}. This is the assistant's name, not the user's name."
        )
        self.active_sessions = set()
        self.active_tasks = set()

    def session(self, owner, session_id):
        with self.store.db() as db:
            if session_id:
                session = db.get(Session, session_id)
                if not session or session.owner != owner:
                    raise ToolError("session_not_found")
            else:
                session = Session(owner=owner)
                db.add(session)
                db.flush()
            return session.id

    def memories(self, owner, query="", scope=None, category=None):
        with self.store.db() as db:
            stmt = select(Memory).where(
                Memory.owner == owner, or_(Memory.expires_at.is_(None), Memory.expires_at > now())
            )
            if scope:
                stmt = stmt.where(Memory.scope == scope)
            if category:
                stmt = stmt.where(Memory.category == category)
            records = [
                record(m) for m in db.scalars(stmt.order_by(Memory.updated_at.desc()).limit(500))
            ]
        if query:
            terms = set(query.lower().split())
            for m in records:
                m["relevance"] = len(terms & set(m["content"].lower().split())) / max(len(terms), 1)
            records = sorted(
                (m for m in records if m["relevance"] > 0),
                key=lambda m: m["relevance"],
                reverse=True,
            )
        return records

    async def chat(self, owner, request, session_id):
        correlation = uid()

        def event(kind, **payload):
            return Event(
                type=kind, session_id=session_id, correlation_id=correlation, payload=payload
            )

        if session_id in self.active_sessions:
            yield event("error", code="session_busy")
            return
        self.active_sessions.add(session_id)
        started = time.monotonic()
        try:
            yield event("session.started")
            with self.store.db() as db:
                # Only completed user/assistant pairs enter history; failed requests do
                # not leave consecutive user messages incompatible with some providers.
                history = list(
                    reversed(
                        list(
                            db.scalars(
                                select(Message)
                                .where(Message.session_id == session_id)
                                .order_by(Message.created_at.desc())
                                .limit(40)
                            )
                        )
                    )
                )
            if len(request.text) > self.settings.context_char_budget:
                raise ProviderError("context_limit")
            budget = self.settings.context_char_budget - len(request.text)
            messages = []
            for m in reversed(history):
                if len(m.content) > budget:
                    break
                budget -= len(m.content)
                messages.insert(0, {"role": m.role, "content": m.content})
            while messages and messages[0]["role"] != "user":
                messages.pop(0)
            messages.append({"role": "user", "content": request.text})
            memories = self.memories(owner, request.text)[:5]
            context = json.dumps([m["content"] for m in memories], ensure_ascii=False)[:4000]
            system = (
                self.system
                + "\nResponse mode: "
                + request.mode
                + ". Fast means brief; deep means detailed evidence and explanations; "
                "agentic means propose steps, never execute through chat.\n"
                + "Untrusted memory data (JSON):\n"
                + context
            )
            yield event("message.received", mode=request.mode)
            output, usage = "", {}
            async with asyncio.timeout(
                self.settings.provider_timeout * (self.settings.provider_retries + 1)
            ):
                async for chunk in self.provider.stream(messages, system):
                    if chunk.text:
                        output += chunk.text
                        if len(output) > 100000:
                            raise ProviderError("output_limit")
                        yield event("assistant.delta", text=chunk.text)
                    if chunk.usage:
                        usage = chunk.usage
            if not output.strip():
                raise ProviderError("empty_provider_response")
            with self.store.db() as db:
                db.add(Message(session_id=session_id, role="user", content=request.text))
                db.flush()
                db.add(Message(session_id=session_id, role="assistant", content=output))
            yield event(
                "assistant.completed",
                text=output,
                usage=usage,
                latency_ms=round((time.monotonic() - started) * 1000),
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            yield event(
                "error", code=exc.code if isinstance(exc, ProviderError) else "request_failed"
            )
        finally:
            self.active_sessions.discard(session_id)

    def create_plan(self, owner, plan: PlanInput):
        seen = set()
        for step in plan.steps:
            if step.id in seen or not set(step.depends_on) <= seen:
                raise ToolError("invalid_dependencies")
            self.registry.validate(step.tool, step.arguments)
            seen.add(step.id)
        with self.store.db() as db:
            task = Task(
                owner=owner,
                title=plan.title,
                steps=[dict(s.model_dump(), status="planned") for s in plan.steps],
            )
            db.add(task)
            db.flush()
            return record(task)

    async def propose_plan(self, owner, request):
        # One bounded specialist call, no recursive delegation and no action execution.
        system = self.system + (
            f"\nYou are the {request.agent} specialist. Draft a plan using only listed tools. "
            "Return only a JSON object matching this schema: "
            + json.dumps(PlanInput.model_json_schema())
            + "\nAvailable tools: "
            + json.dumps([t.describe() for t in self.registry.tools.values()])
        )
        output = ""
        async with asyncio.timeout(self.settings.provider_timeout):
            async for chunk in self.provider.stream(
                [{"role": "user", "content": request.objective}], system
            ):
                output += chunk.text
                if len(output) > 30000:
                    raise ToolError("invalid_provider_plan")
        try:
            plan = PlanInput.model_validate_json(output)
        except ValueError:
            raise ToolError("invalid_provider_plan") from None
        return self.create_plan(owner, plan)

    async def run_plan(self, owner, task_id):
        if task_id in self.active_tasks:
            raise ToolError("task_busy")
        self.active_tasks.add(task_id)
        try:
            with self.store.db() as db:
                task = db.get(Task, task_id)
                if not task or task.owner != owner:
                    raise ToolError("task_not_found")
                if task.status in {"cancelled", "failed", "completed", "waiting_for_authorization"}:
                    return record(task)
                steps = [dict(s) for s in task.steps]
                task.status = "running"
            for step in steps:
                with self.store.db() as db:
                    if db.get(Task, task_id).status == "cancelled":
                        return record(db.get(Task, task_id))
                if step["status"] == "completed":
                    continue
                if step["status"] == "waiting_for_authorization":
                    break
                if not all(
                    s["status"] == "completed" for s in steps if s["id"] in step["depends_on"]
                ):
                    raise ToolError("dependency_incomplete")
                result = await self.registry.execute(
                    owner, step["tool"], step["arguments"], task_id=task_id, step_id=step["id"]
                )
                step.update(status=result["status"], result=result)
                with self.store.db() as db:
                    task = db.get(Task, task_id)
                    task.steps = steps
                    task.status = result["status"] if result["status"] != "completed" else "running"
                if result["status"] != "completed":
                    break
                await asyncio.sleep(0)  # cooperative cancellation between bounded operations
            with self.store.db() as db:
                task = db.get(Task, task_id)
                if all(s["status"] == "completed" for s in steps):
                    task.status = "completed"
                return record(task)
        finally:
            self.active_tasks.discard(task_id)
