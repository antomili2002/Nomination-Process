"""Report layout policy — the single source of truth for country → layout.

Keeping this decision in one place lets the report service and the Excel writer
dispatch on the same rule, so a new layout is added here rather than edited into
scattered ``== "UK"`` / ``== "non_uk"`` branches.
"""
from __future__ import annotations

LAYOUT_UK = "uk"
LAYOUT_NON_UK = "non_uk"


def layout_for_country(portfolio_country: str) -> str:
    """Return the report layout a portfolio country maps to.

    UK portfolios keep the per-metric tariff layout; every other country uses
    the consolidated IV/EV category layout.
    """
    return LAYOUT_UK if portfolio_country.strip().upper() == "UK" else LAYOUT_NON_UK
