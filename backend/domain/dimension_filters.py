"""Dimension filter domain objects.

DimensionFilters carries optional multi-value filters for the four
combinatorial dimensions (plant, unit, machine, fuel).  None means "all".
FilterOptions holds the full sorted lists available in the uploaded file.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DimensionFilters:
    machine_names: list[str] | None = None
    plant_names: list[str] | None = None
    unit_names: list[str] | None = None
    fuel_names: list[str] | None = None

    def is_empty(self) -> bool:
        return all(v is None for v in (
            self.machine_names, self.plant_names, self.unit_names, self.fuel_names
        ))


@dataclass
class FilterOptions:
    machines: list[str] = field(default_factory=list)
    plant_names: list[str] = field(default_factory=list)
    unit_names: list[str] = field(default_factory=list)
    fuel_names: list[str] = field(default_factory=list)
