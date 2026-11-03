import ast
import asyncio
import inspect
import math
import operator
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jsonschema
from pydantic import BaseModel, Field, ValidationError

from .contracts import StrictModel, now
from .persistence import Approval, Audit, Execution, record


class ToolError(Exception):
    pass


class Empty(StrictModel):
    pass


class Calculation(StrictModel):
    expression: str = Field(min_length=1, max_length=200)


class ReadFile(StrictModel):
    path: str = Field(min_length=1, max_length=300)


class WriteFile(ReadFile):
    content: str = Field(max_length=64000)


class Result(BaseModel):
    value: Any


def calculate(args):
    operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Mod: operator.mod,
    }

    def visit(node, depth=0):
        if depth > 20:
            raise ToolError("expression_too_complex")
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            value = node.value
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = visit(node.operand, depth + 1) * (-1 if isinstance(node.op, ast.USub) else 1)
        elif isinstance(node, ast.BinOp) and type(node.op) in operators:
            value = operators[type(node.op)](
                visit(node.left, depth + 1), visit(node.right, depth + 1)
            )
        else:
            raise ToolError("unsupported_expression")
        if not math.isfinite(value) or abs(value) > 1e100:
            raise ToolError("result_out_of_bounds")
        return value

    return {"value": visit(ast.parse(args.expression, mode="eval").body)}


class Files:
    """Use dir-fd and O_NOFOLLOW for every path segment; no symlink traversal."""

    def __init__(self, root):
        self.root = Path(root).absolute()
        self.root.mkdir(parents=True, exist_ok=True)

    def open(self, name, flags):
        parts = name.split("/")
        if any(p in {"", ".", ".."} for p in parts) or "\\" in name:
            raise ToolError("invalid_path")
        fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            for part in parts[:-1]:
                nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = nxt
            return os.open(parts[-1], flags | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=fd)
        finally:
            os.close(fd)

    def read(self, args):
        import stat

        with os.fdopen(self.open(args.path, os.O_RDONLY), "r", encoding="utf-8") as f:
            if not stat.S_ISREG(os.fstat(f.fileno()).st_mode):
                raise ToolError("not_regular_file")
            content = f.read(64001)
        if len(content) > 64000:
            raise ToolError("file_too_large")
        return {"value": content}

    def write(self, args):
        # Create-only: existing files cannot be overwritten by this tool.
        with os.fdopen(self.open(args.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL), "w") as f:
            f.write(args.content)
            f.flush()
            os.fsync(f.fileno())
        if self.read(ReadFile(path=args.path))["value"] != args.content:
            raise ToolError("verification_failed")
        return {"value": {"path": args.path, "characters": len(args.content), "verified": True}}


@dataclass
class Tool:
    name: str
    description: str
    schema: type[BaseModel]
    handler: Callable
    risk: int = 0
    permission: str = "informational"
    timeout: float = 5
    json_schema: dict | None = None

    def describe(self):
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.json_schema or self.schema.model_json_schema(),
            "output_schema": Result.model_json_schema(),
            "risk": self.risk,
            "required_permission": self.permission,
            "timeout_seconds": self.timeout,
            "available": True,
            "errors": ["invalid_arguments", "tool_failed", "timeout"],
        }


class Registry:
    def __init__(self, settings, store):
        self.store = store
        files = Files(settings.files_root)
        self.tools = {
            t.name: t
            for t in [
                Tool("calculate", "Bounded arithmetic, no code execution", Calculation, calculate),
                Tool(
                    "time",
                    "Current UTC date and time",
                    Empty,
                    lambda _: {"value": now().isoformat()},
                ),
                Tool(
                    "file.read",
                    "Read UTF-8 within FILES_ROOT",
                    ReadFile,
                    files.read,
                    1,
                    "files.read",
                ),
                Tool(
                    "file.create",
                    "Create and verify a new UTF-8 file within FILES_ROOT",
                    WriteFile,
                    files.write,
                    2,
                    "files.create",
                ),
            ]
        }

    def validate(self, name, arguments):
        tool = self.tools.get(name)
        if not tool:
            raise ToolError("unknown_tool")
        try:
            if tool.json_schema:
                jsonschema.validate(arguments, tool.json_schema)
            return tool, tool.schema.model_validate(arguments)
        except (ValidationError, jsonschema.ValidationError):
            raise ToolError("invalid_arguments") from None

    async def execute(
        self, owner, name, arguments, *, authorized=False, task_id=None, step_id=None
    ):
        tool, parsed = self.validate(name, arguments)
        if tool.risk >= 2 and not authorized:
            with self.store.db() as db:
                approval = Approval(
                    owner=owner,
                    tool=name,
                    arguments=parsed.model_dump(),
                    task_id=task_id,
                    step_id=step_id,
                )
                db.add(approval)
                db.flush()
                db.add(Audit(owner=owner, action="approval.requested", resource_id=approval.id))
                return {"status": "waiting_for_authorization", "approval_id": approval.id}
        try:
            # Built-in handlers are strictly bounded local operations. Running them directly
            # avoids abandoned worker threads continuing a write after cancellation/timeout.
            if inspect.iscoroutinefunction(tool.handler):
                async with asyncio.timeout(tool.timeout):
                    raw = await tool.handler(parsed)
            else:
                raw = tool.handler(parsed)
            result = Result.model_validate(raw).model_dump()
            status = "completed"
        except Exception:
            status, result = "failed", {"error": "tool_failed"}
        with self.store.db() as db:
            execution = Execution(owner=owner, tool=name, status=status, result=result)
            db.add(execution)
            db.flush()
            db.add(Audit(owner=owner, action=f"tool.{status}", resource_id=execution.id))
            return {"status": status, "execution_id": execution.id, "result": result}

    async def decision(self, owner, approval_id, approve):
        # Atomic claim prevents replay/concurrent double execution. On crash a claimed
        # action is never retried automatically (at-most-once, outcome may be unknown).
        from sqlalchemy import update

        with self.store.db() as db:
            changed = db.execute(
                update(Approval)
                .where(
                    Approval.id == approval_id,
                    Approval.owner == owner,
                    Approval.status == "pending",
                )
                .values(status="executing" if approve else "denied")
            )
            if changed.rowcount != 1:
                raise ToolError("approval_not_pending")
            approval = db.get(Approval, approval_id)
            data = record(approval)
            db.add(
                Audit(
                    owner=owner,
                    action="approval.approved" if approve else "approval.denied",
                    resource_id=approval_id,
                )
            )
        result = {"status": "denied"}
        if approve:
            result = await self.execute(owner, data["tool"], data["arguments"], authorized=True)
            with self.store.db() as db:
                db.get(Approval, approval_id).status = result["status"]
        if data["task_id"]:
            from .persistence import Task

            with self.store.db() as db:
                task = db.get(Task, data["task_id"])
                steps = [dict(s) for s in task.steps]
                for step in steps:
                    if step["id"] == data["step_id"]:
                        step.update(status=result["status"], result=result)
                task.steps = steps
                task.status = "planned" if result["status"] == "completed" else "failed"
        return result
