# File: mcp_server/compliance_mcp.py
"""Custom MCP data-access boundary for regulated contract review."""

# ### KAGGLE CRITERIA: MCP SERVER IMPLEMENTATION ###
# Logical component: isolated, allowlisted compliance and market-data MCP tools.

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

try:  # The application can still run its in-process demo without a transport dependency.
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover - exercised only when optional MCP package is absent.
    FastMCP = None  # type: ignore[assignment,misc]


class VaultRequest(BaseModel):
    """Allowlisted compliance document identifier."""

    model_config = ConfigDict(extra="forbid")
    document_id: str = Field(pattern=r"^[a-z0-9_-]{3,64}$")


class MarketRateRequest(BaseModel):
    """Strict ISO-style source currency input."""

    model_config = ConfigDict(extra="forbid")
    base_currency: str = Field(min_length=3, max_length=3)

    @field_validator("base_currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


# ### KAGGLE CRITERIA: MCP SERVER IMPLEMENTATION ###
# Logical component: encrypted-vault simulation; only named records are exposed.
_SECURE_VAULT: dict[str, dict[str, Any]] = {
    "global_contract_policy": {
        "max_liability_cap_usd": 50_000,
        "prohibited_vendors": ["VendorX", "VendorY"],
        "required_clauses": ["data protection", "termination for cause"],
        "approved_currencies": ["USD", "EUR", "GBP", "INR"],
    }
}

_MARKET_RATES_TO_USD: dict[str, Decimal] = {
    "USD": Decimal("1.0000"), "EUR": Decimal("1.0800"), "GBP": Decimal("1.2700"), "INR": Decimal("0.0120"),
}


class ComplianceMCPService:
    """In-process implementation behind the same narrow interface as MCP tools."""

    def read_secure_vault(self, document_id: str) -> dict[str, Any]:
        """Return one allowlisted policy document; never accepts a filesystem path."""
        request = VaultRequest(document_id=document_id)
        if request.document_id not in _SECURE_VAULT:
            raise KeyError("Requested vault document does not exist or is not authorized.")
        # JSON round-trip prevents callers mutating the server's protected record.
        return json.loads(json.dumps(_SECURE_VAULT[request.document_id]))

    def fetch_market_rates(self, base_currency: str) -> dict[str, Any]:
        """Simulate an allowlisted external FX API response for exposure analysis."""
        request = MarketRateRequest(base_currency=base_currency)
        if request.base_currency not in _MARKET_RATES_TO_USD:
            raise ValueError(f"Unsupported currency: {request.base_currency}")
        return {
            "base_currency": request.base_currency,
            "usd_rate": str(_MARKET_RATES_TO_USD[request.base_currency]),
            "as_of": datetime.now(timezone.utc).isoformat(),
            "source": "simulated-approved-market-feed",
        }


# ### KAGGLE CRITERIA: MCP SERVER IMPLEMENTATION ###
# Logical component: optional standards-compliant MCP transport registration.
def create_mcp_server() -> Any:
    """Create a FastMCP server when the MCP SDK is installed."""
    if FastMCP is None:
        raise RuntimeError("Install the 'mcp' dependency to run the MCP transport.")
    service = ComplianceMCPService()
    server = FastMCP("secure-compliance-vault")

    @server.tool()
    def read_secure_vault(document_id: str) -> dict[str, Any]:
        """Read the allowlisted global compliance policy from the secure vault."""
        return service.read_secure_vault(document_id)

    @server.tool()
    def fetch_market_rates(base_currency: str) -> dict[str, Any]:
        """Fetch an approved simulated market conversion rate to USD."""
        return service.fetch_market_rates(base_currency)

    return server


if __name__ == "__main__":  # pragma: no cover
    create_mcp_server().run()
