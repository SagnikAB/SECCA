<!-- File: README.md -->

# Secure Enterprise Contract & Compliance Agent

An enterprise-ready, demonstrable multi-agent workflow for contract review, built around Google ADK-style graph design and an isolated custom Model Context Protocol (MCP) server. It is designed as a Kaggle **AI Agents: Intensive Vibe Coding Capstone Project** submission for the **Agents for Business** track.

The project deliberately puts compliance before financial analysis: untrusted input is screened first, policy is retrieved only through a narrow MCP boundary, then specialists produce a deterministic, auditable verdict.

## Kaggle evaluation mapping

| Evaluation area | Implementation |
| --- | --- |
| Agent / multi-agent system (ADK) | Typed shared state and Router, Compliance, Financial Analyst, and Decision agents in `agents/orchestrator.py`. |
| MCP server implementation | Allowlisted `read_secure_vault` and `fetch_market_rates` tools, plus an optional FastMCP transport, in `mcp_server/compliance_mcp.py`. |
| Security features | Pydantic schemas, control-character checks, prompt-injection and path-traversal blocking, and an explicit `SecurityException` in `core/security_engine.py`. |
| Deployability / Agent Skills CLI | JSON-line execution tracing of state mutations, latency, estimated tokens, tool arguments, and failures in `utils/observability.py`. |
| Documentation | This guide, architecture, setup, security posture, test instructions, and extension notes. |

Every production component contains `### KAGGLE CRITERIA` structural comments that map its purpose directly to the judging criteria.

## Architecture

```text
                         untrusted contract text
                                   |
                                   v
                  +-------------------------------+
                  | Pydantic + Security Engine     |
                  | injection / traversal firewall |
                  +-------------------------------+
                       | safe                 | blocked
                       v                      v
        +--------------------------------+   SecurityException
        | ADK-style Contract Agent Graph |
        |  Router -> Compliance -> Final |
        |              |                 |
        |              +-> Financial -----+
        +--------------------------------+
                   |               |
                   v               v
        +----------------+  +---------------------+
        | MCP compliance |  | JSON trace emitter   |
        | vault tools    |  | state/latency/tokens |
        +----------------+  +---------------------+
```

## Repository layout

```text
agents/orchestrator.py       ADK-style graph, shared state, and agent nodes
core/security_engine.py      validation and hostile-input guardrails
mcp_server/compliance_mcp.py custom MCP service and optional FastMCP server
utils/observability.py       structured JSON observability
main.py                      runnable demonstration lifecycle
app.py                       Streamlit enterprise review interface
tests/                       security and workflow regression tests
```

## Run locally

Requires Python 3.10+.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

The application prints JSON trace records to stderr and a final machine-readable compilation report to stdout. The included example deliberately contains a prohibited vendor and an excessive liability cap, so the final verdict is a rejection.

## Interactive UI

Launch the local review console with:

```powershell
streamlit run app.py
```

The browser UI provides sample contracts, a contract editor, a compliance-finding view, USD exposure calculation, and a downloadable JSON audit trail. It uses exactly the same security gate, MCP service, agent graph, and trace events as the command-line application.

Run the regression suite with:

```powershell
pip install -e ".[dev]"
pytest -q
```

To expose the MCP tools to an MCP-capable client after installing dependencies:

```powershell
python -m mcp_server.compliance_mcp
```

## Security model

- The agent graph never receives input until `sanitize_contract_input` validates it. A `SecurityException` stops execution before a router node or MCP tool call.
- The vault tool accepts an identifier matching a strict allowlist schema, never a filename or path. It returns a copied policy record to prevent caller-side mutation.
- Market-rate inputs are constrained to normalized three-character currencies and an approved local feed; no live credentials or external network request are needed for the demo.
- Traces redact long string fields, preserving operational evidence without emitting the full contract body.
- This is a reference architecture: production adoption should replace the simulated vault with KMS-backed storage, authenticate MCP callers, authorize by tenant, redact according to a formal data-classification policy, and ship traces to an immutable SIEM.

## Extending it with Google ADK

The graph follows ADK’s practical design principle: focused agents share typed state, tools sit behind a constrained interface, and routing is explicit and observable. To integrate a live Google ADK deployment, adapt each `*_agent` method into an ADK agent callback and expose `ComplianceMCPService` via an MCP client tool. The sequencing and security gate should remain outside model control.

## Reproducibility

All policy and FX values are deterministic fixtures except the `as_of` timestamp. This enables repeatable test assertions, demonstrations without credentials, and transparent inspection of every policy decision.
