"""Vercel serverless endpoint for Contract Sentinel assessments."""

from __future__ import annotations

from flask import Flask, jsonify, request

from agents.orchestrator import ContractAgentGraph
from core.security_engine import SecurityException
from mcp_server.compliance_mcp import ComplianceMCPService
from utils.observability import ExecutionTracer


app = Flask(__name__)


@app.post("/api/analyze")
def analyze():
    """Run the guarded contract workflow and return only safe review data."""
    payload = request.get_json(silent=True) or {}
    contract_text = payload.get("contract_text")
    if not isinstance(contract_text, str) or not contract_text.strip():
        return jsonify({"error": "Provide contract text to assess."}), 400

    tracer = ExecutionTracer()
    graph = ContractAgentGraph(ComplianceMCPService(), tracer)
    try:
        report = graph.run(contract_text)
    except SecurityException as exc:
        return jsonify({"error": "Assessment stopped by the security gate.", "detail": str(exc)}), 422

    return jsonify({"report": report.model_dump(), "run_id": tracer.run_id, "events": tracer.events})
