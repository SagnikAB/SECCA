# File: agents/orchestrator.py
"""Deterministic multi-agent graph modeled on Google ADK orchestration patterns."""

# ### KAGGLE CRITERIA: AGENT / MULTI-AGENT SYSTEM (ADK) ###
# Logical component: typed shared state and conditional multi-agent graph routing.

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

from core.security_engine import SecureAgentOutput, sanitize_contract_input
from mcp_server.compliance_mcp import ComplianceMCPService
from utils.observability import ExecutionTracer


@dataclass
class ContractState:
    """Shared state passed through ADK-style specialist agent nodes."""

    contract_text: str
    compliance_flags: list[str] = field(default_factory=list)
    financial_exposure: dict[str, Any] = field(default_factory=dict)
    final_verdict: str = "PENDING"
    route: str = ""


class ContractAgentGraph:
    """A small, inspectable graph whose nodes emulate ADK agent responsibilities."""

    def __init__(self, mcp_service: ComplianceMCPService, tracer: ExecutionTracer) -> None:
        self.mcp_service = mcp_service
        self.tracer = tracer

    # ### KAGGLE CRITERIA: AGENT / MULTI-AGENT SYSTEM (ADK) ###
    # Logical component: Router Agent selects the verification graph path.
    def router_agent(self, state: ContractState) -> Literal["compliance", "financial", "both"]:
        lower = state.contract_text.lower()
        has_financial = bool(re.search(r"\b(?:usd|eur|gbp|inr|currency|payment|liability|\$)\b", lower))
        state.route = "both" if has_financial else "compliance"
        return state.route  # Compliance is always first: it is the policy gate.

    # ### KAGGLE CRITERIA: AGENT / MULTI-AGENT SYSTEM (ADK) ###
    # Logical component: Compliance Agent uses MCP vault policy to identify risk.
    def compliance_agent(self, state: ContractState) -> None:
        arguments = {"document_id": "global_contract_policy"}
        self.tracer.tool_call("read_secure_vault", arguments)
        policy = self.mcp_service.read_secure_vault(**arguments)
        text = state.contract_text.lower()
        for vendor in policy["prohibited_vendors"]:
            if vendor.lower() in text:
                state.compliance_flags.append(f"BLOCKER: prohibited vendor detected ({vendor}).")
        liability_match = re.search(r"(?:liability cap|liability).*?\$?([\d,]+)", text)
        if liability_match:
            amount = int(liability_match.group(1).replace(",", ""))
            if amount > policy["max_liability_cap_usd"]:
                state.compliance_flags.append(f"BLOCKER: liability cap ${amount:,} exceeds ${policy['max_liability_cap_usd']:,} policy limit.")
        for clause in policy["required_clauses"]:
            if clause not in text:
                state.compliance_flags.append(f"REVIEW: required clause missing: {clause}.")

    # ### KAGGLE CRITERIA: AGENT / MULTI-AGENT SYSTEM (ADK) ###
    # Logical component: Financial Analyst Agent uses MCP FX rates for cross-border exposure.
    def financial_analyst_agent(self, state: ContractState) -> None:
        match = re.search(r"(?:payment|value|fee|amount|liability)[^\n.]{0,80}?\b(USD|EUR|GBP|INR)\s*([\d,]+(?:\.\d{1,2})?)", state.contract_text, re.IGNORECASE)
        if not match:
            state.financial_exposure = {"status": "not_applicable", "reason": "No parsable cross-border monetary amount found."}
            return
        currency, raw_amount = match.group(1).upper(), match.group(2).replace(",", "")
        arguments = {"base_currency": currency}
        self.tracer.tool_call("fetch_market_rates", arguments)
        rate = self.mcp_service.fetch_market_rates(**arguments)
        try:
            amount = Decimal(raw_amount)
            usd_exposure = amount * Decimal(rate["usd_rate"])
        except InvalidOperation as exc:
            raise ValueError("Could not safely parse contract monetary amount.") from exc
        state.financial_exposure = {"source_currency": currency, "source_amount": str(amount), "usd_rate": rate["usd_rate"], "usd_exposure": f"{usd_exposure:.2f}", "rate_as_of": rate["as_of"]}

    # ### KAGGLE CRITERIA: AGENT / MULTI-AGENT SYSTEM (ADK) ###
    # Logical component: Final Decision Agent compiles specialist outcomes after policy verification.
    def final_decision_agent(self, state: ContractState) -> None:
        if any(flag.startswith("BLOCKER") for flag in state.compliance_flags):
            state.final_verdict = "REJECTED — resolve policy blockers before execution."
        elif state.compliance_flags:
            state.final_verdict = "CONDITIONAL APPROVAL — legal review required for flagged clauses."
        else:
            state.final_verdict = "APPROVED — no configured policy violations detected."

    def _invoke(self, name: str, state: ContractState, function: Any) -> None:
        before = asdict(state)
        with self.tracer.span(name, token_estimate=max(1, len(state.contract_text) // 4)):
            function(state)
        self.tracer.state_change(name, before, asdict(state))

    def run(self, contract_text: str) -> SecureAgentOutput:
        """Execute the ordered graph; validation happens before any agent or MCP tool."""
        safe_text = sanitize_contract_input(contract_text)
        state = ContractState(contract_text=safe_text)
        self._invoke("router_agent", state, self.router_agent)
        self._invoke("compliance_agent", state, self.compliance_agent)
        if state.route == "both":
            self._invoke("financial_analyst_agent", state, self.financial_analyst_agent)
        self._invoke("final_decision_agent", state, self.final_decision_agent)
        return SecureAgentOutput(final_verdict=state.final_verdict, compliance_flags=state.compliance_flags, financial_exposure=state.financial_exposure)
