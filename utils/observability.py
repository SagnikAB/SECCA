# File: utils/observability.py
"""Structured, redacted execution tracing for agent workflows."""

# ### KAGGLE CRITERIA: DEPLOYABILITY & AGENT SKILLS CLI ###
# Logical component: JSON tracing of state transitions, latency, token estimates, and MCP arguments.

from __future__ import annotations

import json
import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Generator
from uuid import uuid4


def _safe(value: Any) -> Any:
    """Make trace payloads JSON-safe without logging raw contract text."""
    if isinstance(value, str) and len(value) > 200:
        return {"redacted": True, "characters": len(value)}
    if isinstance(value, dict):
        return {key: _safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_safe(item) for item in value]
    return value


@dataclass
class ExecutionTracer:
    """Captures structured events suitable for a CLI, SIEM, or trace collector."""

    logger: logging.Logger = field(default_factory=lambda: logging.getLogger("contract_agent.trace"))
    run_id: str = field(default_factory=lambda: str(uuid4()))
    events: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(message)s"))
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

    def log(self, event: str, **payload: Any) -> None:
        record = {"timestamp": datetime.now(timezone.utc).isoformat(), "run_id": self.run_id, "event": event, **_safe(payload)}
        self.events.append(record)
        self.logger.info(json.dumps(record, default=str, sort_keys=True))

    def state_change(self, node: str, before: dict[str, Any], after: dict[str, Any]) -> None:
        changed = {key: after[key] for key in after if before.get(key) != after[key]}
        self.log("state_change", node=node, changed=changed)

    def tool_call(self, tool: str, arguments: dict[str, Any]) -> None:
        self.log("mcp_tool_call", tool=tool, arguments=arguments)

    @contextmanager
    def span(self, node: str, token_estimate: int = 0) -> Generator[None, None, None]:
        started = time.perf_counter()
        self.log("agent_started", node=node)
        try:
            yield
        except Exception as exc:
            self.log("agent_failed", node=node, error_type=type(exc).__name__, error=str(exc))
            raise
        finally:
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            self.log("agent_completed", node=node, duration_ms=elapsed_ms, token_estimate=token_estimate)
