#Engineer Decisions Log

##ADR-0001

Title:
Keep pycomm3 confined to the discovery layer.

Decision:
The model shall never import pycomm3 directly.

Reason:
Allows future replacement with a native CIP implementation or
offline parsers (L5X, ACD, EDS) without affecting the domain model.

Status:
Accepted

ADR-0002 — Model physical assets separately from logical entities.
ADR-0003 — Use dataclasses for all domain objects.
ADR-0004 — Build the twin from live data first, then enrich it with offline artifacts.
ADR-0005 — Introduce Channel and Assembly only when supported by real CIP discovery.
