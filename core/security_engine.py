# File: core/security_engine.py
"""Runtime validation and prompt-injection defenses."""

# ### KAGGLE CRITERIA: SECURITY FEATURES ###
# Logical component: input/output validation and pipeline short-circuit controls.

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SecurityException(ValueError):
    """Raised when untrusted input violates the contract-agent security policy."""


class ContractInput(BaseModel):
    """Strict schema for untrusted contract content entering the agent graph."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    contract_text: str = Field(min_length=20, max_length=100_000)

    @field_validator("contract_text")
    @classmethod
    def reject_control_characters(cls, value: str) -> str:
        if any(ord(character) < 32 and character not in "\n\r\t" for character in value):
            raise ValueError("Contract contains disallowed control characters.")
        return value


class SecureAgentOutput(BaseModel):
    """Sanitized public result shape emitted by the application."""

    model_config = ConfigDict(extra="forbid")
    final_verdict: str
    compliance_flags: list[str]
    financial_exposure: dict[str, Any]


# ### KAGGLE CRITERIA: SECURITY FEATURES ###
# Logical component: deterministic prompt-injection and sandbox-escape detection.
_BLOCKED_PATTERNS: dict[str, re.Pattern[str]] = {
    "path traversal": re.compile(r"(?:\.\.[\\/]|[\\/]\.\.(?:[\\/]|$))", re.IGNORECASE),
    "instruction override": re.compile(
        r"\b(?:ignore|disregard|override)\s+(?:all\s+)?(?:previous|prior|system)\s+(?:instructions?|rules?)\b",
        re.IGNORECASE,
    ),
    "prompt extraction": re.compile(r"\b(?:reveal|print|show)\s+(?:the\s+)?(?:system prompt|hidden instructions)\b", re.IGNORECASE),
    "tool exfiltration": re.compile(r"\b(?:read_secure_vault|fetch_market_rates)\s*\([^)]*(?:secret|token|password)", re.IGNORECASE),
}


def sanitize_contract_input(text: str) -> str:
    """Validate and normalize contract text, raising before any tool can execute."""

    try:
        normalized = ContractInput(contract_text=text).contract_text
    except Exception as exc:  # Convert schema errors into one pipeline-safe exception.
        raise SecurityException(f"Invalid contract input: {exc}") from exc

    for label, pattern in _BLOCKED_PATTERNS.items():
        if pattern.search(normalized):
            raise SecurityException(f"Blocked {label} attempt in contract input.")
    return normalized
