# File: app.py
"""Streamlit UI for the Secure Enterprise Contract & Compliance Agent."""

# ### KAGGLE CRITERIA: DEPLOYABILITY & AGENT SKILLS CLI ###
# Logical component: user-facing operational console for the secure multi-agent workflow.

from __future__ import annotations

import json
from typing import Any

import streamlit as st

from agents.orchestrator import ContractAgentGraph
from core.security_engine import SecurityException
from mcp_server.compliance_mcp import ComplianceMCPService
from utils.observability import ExecutionTracer


EXAMPLE_CONTRACT = """Master Services Agreement: VendorX will provide analytics services.
The contract sets a liability cap of $75,000 and payment of EUR 120,000.
This agreement contains a data protection clause but no termination for cause language.
"""

SAFE_CONTRACT = """Services Agreement: VendorA will provide analytics services.
The liability cap is $40,000. Payment is EUR 20,000.
This agreement includes data protection and termination for cause clauses.
"""


def initialise_page() -> None:
    """Configure a wide, restrained enterprise review surface."""
    st.set_page_config(page_title="Contract Sentinel", page_icon="🛡️", layout="wide")
    st.markdown(
        """<style>
        .stApp { background: #f6f8fb; }
        .block-container { max-width: 1320px; padding-top: 2.5rem; }
        [data-testid="stMetric"] { background: white; border: 1px solid #e7ecf3; border-radius: 12px; padding: 16px; }
        .hero { padding: 1.5rem 0 1.2rem; }
        .eyebrow { color: #316bff; font-size: .76rem; font-weight: 750; letter-spacing: .11em; text-transform: uppercase; }
        .hero h1 { margin: .15rem 0 .35rem; font-size: 2.35rem; color: #13233a; }
        .hero p { color: #607087; font-size: 1.05rem; max-width: 48rem; }
        .verdict { padding: 1rem 1.1rem; border-radius: 10px; font-weight: 650; }
        .verdict-rejected { background: #fff0f0; border: 1px solid #ffcaca; color: #9c2020; }
        .verdict-conditional { background: #fff8e8; border: 1px solid #f4d48c; color: #865b00; }
        .verdict-approved { background: #edfaf1; border: 1px solid #ace2bd; color: #166534; }
        </style>""",
        unsafe_allow_html=True,
    )


def severity(flag: str) -> str:
    """Map deterministic policy flags to visual severity."""
    return "🔴 Blocker" if flag.startswith("BLOCKER") else "🟠 Review"


def show_report(report: Any, tracer: ExecutionTracer) -> None:
    """Render the sanitized result and auditable execution record."""
    verdict = report.final_verdict
    if verdict.startswith("REJECTED"):
        verdict_class = "verdict-rejected"
    elif verdict.startswith("CONDITIONAL"):
        verdict_class = "verdict-conditional"
    else:
        verdict_class = "verdict-approved"
    st.markdown(f'<div class="verdict {verdict_class}">{verdict}</div>', unsafe_allow_html=True)
    st.caption(f"Execution ID: `{tracer.run_id}`")

    flags, exposure_column = st.columns((1.25, 1))
    with flags:
        st.subheader("Compliance findings")
        if report.compliance_flags:
            for flag in report.compliance_flags:
                st.write(f"**{severity(flag)}** — {flag.split(': ', 1)[-1]}")
        else:
            st.success("No configured policy violations detected.")
    with exposure_column:
        st.subheader("Financial exposure")
        financial_exposure = report.financial_exposure
        if financial_exposure:
            if financial_exposure.get("status") == "not_applicable":
                st.info(financial_exposure["reason"])
            else:
                st.metric("USD exposure", f"${float(financial_exposure['usd_exposure']):,.2f}")
                st.caption(f"{financial_exposure['source_currency']} {financial_exposure['source_amount']} × {financial_exposure['usd_rate']} USD")
                st.caption(f"Rate timestamp: {financial_exposure['rate_as_of']}")

    st.subheader("Execution audit trail")
    st.caption("Events include state mutations, MCP tool arguments, latency, and token estimates. Contract text is redacted in traces.")
    st.dataframe(tracer.events, use_container_width=True, hide_index=True)
    st.download_button(
        "Download audit JSON",
        data=json.dumps(tracer.events, indent=2, default=str),
        file_name=f"contract-sentinel-audit-{tracer.run_id}.json",
        mime="application/json",
    )


def main() -> None:
    """Run the interactive contract-assessment experience."""
    initialise_page()
    st.markdown("""<div class="hero"><div class="eyebrow">Secure enterprise workflow</div>
    <h1>Contract Sentinel</h1><p>Review commercial agreements through a guarded multi-agent compliance and financial-risk pipeline.</p></div>""", unsafe_allow_html=True)

    st.sidebar.header("Analysis controls")
    example_choice = st.sidebar.radio("Load a starter contract", ["Risky example", "Compliant example", "Keep editor text"], index=0)
    st.sidebar.markdown("---")
    st.sidebar.caption("Security gate active")
    st.sidebar.caption("Prompt injection and path traversal are blocked before any agent or MCP tool runs.")

    default_text = EXAMPLE_CONTRACT if example_choice == "Risky example" else SAFE_CONTRACT if example_choice == "Compliant example" else st.session_state.get("contract_text", EXAMPLE_CONTRACT)
    with st.form("contract-review-form"):
        contract_text = st.text_area("Contract content", value=default_text, height=300, help="Paste the contract text to review. This demo does not persist it.")
        submitted = st.form_submit_button("Run secure assessment", type="primary", use_container_width=True)

    if not submitted:
        st.info("Choose a starter contract or paste your own, then run the secure assessment.")
        return

    st.session_state["contract_text"] = contract_text
    tracer = ExecutionTracer()
    graph = ContractAgentGraph(ComplianceMCPService(), tracer)
    try:
        with st.spinner("Security gate and agent graph running…"):
            report = graph.run(contract_text)
    except SecurityException as exc:
        st.error("Assessment blocked by the security gate.")
        st.code(str(exc), language=None)
        st.caption("No MCP tool calls were permitted.")
        return
    show_report(report, tracer)


if __name__ == "__main__":
    main()
