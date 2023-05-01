from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True, slots=True)
class Building:
    id: str
    name: str


@dataclass(frozen=True, kw_only=True, slots=True)
class AccessPoint:
    id: str
    legacy_id: str
    name: str
    building: Building
    capabilities: list[str]


@dataclass(frozen=True, kw_only=True, slots=True)
class Tenant:
    id: str
    name: str
    access_points: list[AccessPoint]
