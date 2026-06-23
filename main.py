# File: main.py
"""Application entry point for Secure Enterprise Contract & Compliance Agent."""

# ### KAGGLE CRITERIA: APPLICATION ENTRY POINT ###
# Logical component: application lifecycle, guardrail execution, tracing, and final report.

from __future__ import annotations

import json

from agents.orchestrator import ContractAgentGraph
from core.security_engine import SecurityException
from mcp_server.compliance_mcp import ComplianceMCPService
from utils.observability import ExecutionTracer


DEMO_CONTRACT = """Master Services Agreement: VendorX will provide analytics services.
The contract sets a liability cap of $75,000 and payment of EUR 120,000.
This agreement contains a data protection clause but no termination for cause language.
"""


def main() -> int:
    tracer = ExecutionTracer()
    service = ComplianceMCPService()
    graph = ContractAgentGraph(service, tracer)
    try:
        report = graph.run(DEMO_CONTRACT)
    except SecurityException as exc:
        tracer.log("pipeline_blocked", reason=str(exc))
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, indent=2))
        return 2
    print(json.dumps({"status": "COMPLETED", "run_id": tracer.run_id, "report": report.model_dump()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
