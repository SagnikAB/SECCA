"""Streamlit UI for the Secure Enterprise Contract & Compliance Agent."""

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
    """Configure a polished, high-legibility review workspace."""
    st.set_page_config(page_title="Contract Sentinel", page_icon="🛡️", layout="wide")
    st.markdown(
        """<style>
        :root { --ink:#172033; --muted:#667085; --line:#e7eaf0; --blue:#315efb; }
        .stApp { background: #f7f8fc; color: var(--ink); }
        .block-container { max-width: 1380px; padding: 2rem 2.25rem 3.5rem; }
        #MainMenu, footer { visibility: hidden; }
        [data-testid="stSidebar"] { background: #111a2e; }
        [data-testid="stSidebar"] * { color: #f5f7ff !important; }
        [data-testid="stSidebar"] [data-baseweb="radio"] label { color: #d3dbef !important; }
        [data-testid="stSidebar"] hr { border-color: #2c3852; }
        .brand { display:flex; align-items:center; gap:.8rem; margin-bottom:2.1rem; }
        .brand-mark { width:38px; height:38px; border-radius:11px; display:grid; place-items:center; background:#315efb; color:white; font-size:1.25rem; }
        .brand-name { font-size:1.05rem; font-weight:800; letter-spacing:-.02em; color:#fff; }
        .brand-sub { font-size:.76rem; color:#aab6d2; margin-top:.1rem; }
        .hero { border: 1px solid #e2e7f3; border-radius: 18px; padding: 2rem 2.2rem; background: radial-gradient(circle at 92% 10%, #e6edff 0, transparent 24%), #ffffff; margin-bottom: 1.4rem; }
        .eyebrow { color:#315efb; font-size:.72rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase; margin-bottom:.5rem; }
        .hero h1 { color:#172033; font-size:2.35rem; line-height:1.1; letter-spacing:-.045em; margin:0 0 .65rem; }
        .hero p { color:#5f6b80; font-size:1.05rem; line-height:1.55; max-width:44rem; margin:0; }
        .step { color:#667085; font-size:.83rem; margin:.2rem 0 1rem; }
        .step b { color:#315efb; }
        .section-label { font-size:.76rem; font-weight:800; letter-spacing:.09em; text-transform:uppercase; color:#667085; margin:1.4rem 0 .4rem; }
        .stTextArea textarea { background:#fff !important; border:1px solid #d7ddea !important; border-radius:12px !important; color:#172033 !important; font-size:.98rem !important; line-height:1.55 !important; padding:1rem !important; }
        .stTextArea textarea:focus { border-color:#315efb !important; box-shadow:0 0 0 3px rgba(49,94,251,.12) !important; }
        .stButton button, .stDownloadButton button { border-radius:10px !important; font-weight:700 !important; min-height:2.7rem; }
        [data-testid="stMetric"] { background:#fff; border:1px solid var(--line); border-radius:14px; padding:1.1rem 1.25rem; }
        [data-testid="stMetricLabel"] { color:#667085; font-size:.78rem; font-weight:700; text-transform:uppercase; letter-spacing:.06em; }
        .verdict { padding:1.2rem 1.35rem; border-radius:14px; font-weight:800; font-size:1.03rem; margin:.4rem 0 1.25rem; }
        .verdict-rejected { background:#fff1f2; border:1px solid #fecdd3; color:#9f1239; }
        .verdict-conditional { background:#fffaeb; border:1px solid #fedf89; color:#854d0e; }
        .verdict-approved { background:#ecfdf3; border:1px solid #abefc6; color:#067647; }
        .finding { background:#fff; border:1px solid var(--line); border-left:4px solid #f97066; border-radius:10px; padding:.9rem 1rem; margin:.55rem 0; color:#344054; line-height:1.45; }
        .finding.review { border-left-color:#fdb022; }
        .finding .tag { display:inline-block; margin-right:.5rem; font-size:.68rem; font-weight:800; letter-spacing:.08em; text-transform:uppercase; }
        .finding.blocker .tag { color:#b42318; }.finding.review .tag { color:#b54708; }
        .detail-card { background:#fff; border:1px solid var(--line); border-radius:14px; padding:1.1rem 1.2rem; margin-top:.7rem; }
        .detail-card p { margin:.3rem 0; color:#667085; font-size:.9rem; }.detail-card strong { color:#172033; }
        .audit-note { color:#667085; font-size:.9rem; margin-bottom:.6rem; }
        </style>""",
        unsafe_allow_html=True,
    )


def render_finding(flag: str) -> None:
    """Render a compliance flag as a scannable risk card."""
    is_blocker = flag.startswith("BLOCKER")
    kind = "Blocker" if is_blocker else "Needs review"
    body = flag.split(": ", 1)[-1]
    css_class = "blocker" if is_blocker else "review"
    st.markdown(f'<div class="finding {css_class}"><span class="tag">{kind}</span>{body}</div>', unsafe_allow_html=True)


def show_report(report: Any, tracer: ExecutionTracer) -> None:
    """Render outcome, supporting evidence, and auditable execution record."""
    verdict = report.final_verdict
    verdict_class = "verdict-rejected" if verdict.startswith("REJECTED") else "verdict-conditional" if verdict.startswith("CONDITIONAL") else "verdict-approved"
    st.markdown('<div class="section-label">Assessment outcome</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="verdict {verdict_class}">{verdict}</div>', unsafe_allow_html=True)
    findings_count = len(report.compliance_flags)
    blockers = sum(flag.startswith("BLOCKER") for flag in report.compliance_flags)
    source = report.financial_exposure.get("source_currency", "—") if report.financial_exposure else "—"
    metric_one, metric_two, metric_three = st.columns(3)
    metric_one.metric("Policy findings", findings_count)
    metric_two.metric("Blocking issues", blockers)
    metric_three.metric("Detected currency", source)

    findings_column, finance_column = st.columns((1.25, 1), gap="large")
    with findings_column:
        st.markdown('<div class="section-label">Compliance findings</div>', unsafe_allow_html=True)
        if report.compliance_flags:
            for flag in report.compliance_flags:
                render_finding(flag)
        else:
            st.success("No configured policy violations were detected.")
    with finance_column:
        st.markdown('<div class="section-label">Financial exposure</div>', unsafe_allow_html=True)
        financial_exposure = report.financial_exposure
        if financial_exposure.get("status") == "not_applicable":
            st.info(financial_exposure["reason"])
        elif financial_exposure:
            st.metric("Estimated USD exposure", f"${float(financial_exposure['usd_exposure']):,.2f}")
            st.markdown(f'''<div class="detail-card"><p><strong>Source amount</strong><br>{financial_exposure['source_currency']} {financial_exposure['source_amount']}</p><p><strong>Applied FX rate</strong><br>{financial_exposure['usd_rate']} USD</p><p><strong>Rate date</strong><br>{financial_exposure['rate_as_of']}</p></div>''', unsafe_allow_html=True)

    st.markdown('<div class="section-label">Audit trail</div>', unsafe_allow_html=True)
    st.markdown('<div class="audit-note">Run ID: <code>' + tracer.run_id + '</code> · Contract text is redacted in trace events.</div>', unsafe_allow_html=True)
    with st.expander("View execution events", expanded=False):
        st.dataframe(tracer.events, use_container_width=True, hide_index=True)
    st.download_button("Download audit JSON", data=json.dumps(tracer.events, indent=2, default=str), file_name=f"contract-sentinel-audit-{tracer.run_id}.json", mime="application/json")


def main() -> None:
    """Run the interactive contract-assessment experience."""
    initialise_page()
    with st.sidebar:
        st.markdown('<div class="brand"><div class="brand-mark">🛡</div><div><div class="brand-name">Contract Sentinel</div><div class="brand-sub">Secure review workspace</div></div></div>', unsafe_allow_html=True)
        st.markdown("### Start with a sample")
        example_choice = st.radio("Sample contract", ["Risky example", "Compliant example", "Keep editor text"], index=0, label_visibility="collapsed")
        st.markdown("---")
        st.markdown("### Security status")
        st.success("Security gate active")
        st.caption("Prompt injection and path traversal are blocked before agents or MCP tools run.")

    st.markdown("""<section class="hero"><div class="eyebrow">Contract intelligence</div><h1>Know what needs attention<br>before you sign.</h1><p>Run an auditable review across policy requirements and financial exposure, with a security gate protecting every analysis.</p></section>""", unsafe_allow_html=True)
    st.markdown('<div class="step"><b>01</b> Add contract text &nbsp;·&nbsp; <b>02</b> Run assessment &nbsp;·&nbsp; <b>03</b> Review decision</div>', unsafe_allow_html=True)
    current_text = st.session_state.get("contract_text", EXAMPLE_CONTRACT)
    default_text = EXAMPLE_CONTRACT if example_choice == "Risky example" else SAFE_CONTRACT if example_choice == "Compliant example" else current_text
    with st.form("contract-review-form"):
        st.markdown('<div class="section-label">Contract content</div>', unsafe_allow_html=True)
        contract_text = st.text_area("Paste the agreement text", value=default_text, height=260, label_visibility="collapsed", placeholder="Paste contract content here…")
        submitted = st.form_submit_button("Run secure assessment", type="primary", use_container_width=True)

    if not submitted:
        st.markdown("<div class='detail-card'><strong>Ready when you are.</strong><p>Choose a sample in the sidebar or paste a contract, then run the assessment to see a structured decision.</p></div>", unsafe_allow_html=True)
        return
    st.session_state["contract_text"] = contract_text
    tracer = ExecutionTracer()
    graph = ContractAgentGraph(ComplianceMCPService(), tracer)
    try:
        with st.spinner("Reviewing policy requirements and financial exposure…"):
            report = graph.run(contract_text)
    except SecurityException as exc:
        st.error("Assessment stopped by the security gate.")
        st.code(str(exc), language=None)
        st.caption("No MCP tool calls were permitted.")
        return
    show_report(report, tracer)


if __name__ == "__main__":
    main()
