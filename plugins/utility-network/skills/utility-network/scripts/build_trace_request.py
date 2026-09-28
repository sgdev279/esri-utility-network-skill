#!/usr/bin/env python3
"""Build or check a UtilityNetworkServer /trace request body.

Catches the mistakes that make REST traces silently return the wrong thing:
unknown traceType, starting points without terminalId/percentAlong (silently
ignored by the service), unknown traceConfiguration keys, bad operators,
numeric values not sent as strings, subnetwork traces missing tier/domain.

Usage:
  # check an existing request (JSON with traceType/traceLocations/traceConfiguration)
  python build_trace_request.py --check request.json

  # build a request and print form-encoded parameters
  python build_trace_request.py --type downstream \
      --start "{GUID}:terminal=1" --start "{GUID2}:along=0.5" \
      --barrier "{GUID3}:terminal=2" --config config.json [--version sde.DEFAULT]
"""
import argparse
import json
import sys

TRACE_TYPES = {"connected", "subnetwork", "subnetworkController", "upstream", "downstream",
               "loops", "shortestPath", "isolation"}
OPERATORS = {"equal", "notEqual", "greaterThan", "greaterThanEqual", "lessThan", "lessThanEqual",
             "includesTheValues", "doesNotIncludeTheValues", "includesAny", "doesNotIncludeAny"}
FUNCTION_TYPES = {"add", "subtract", "average", "count", "min", "max"}
SCOPES = {"junctions", "edges", "junctionsAndEdges"}
CONFIG_KEYS = {
    # booleans / names (see rest-api/01)
    "includeContainers", "includeContent", "includeStructures", "includeBarriers",
    "validateConsistency", "validateLocatability", "synthesizeGeometries", "includeIsolated",
    "ignoreBarriersAtStartingPoints", "includeUpToFirstSpatialContainer",
    "allowIndeterminateFlow", "useDigitizedDirection", "domainNetworkName", "tierName",
    "targetTierName", "subnetworkName", "diagramTemplateName",
    # structured (see rest-api/08)
    "conditionBarriers", "functionBarriers", "filterBarriers", "filterFunctionBarriers",
    "functions", "outputFilters", "outputConditions", "propagators", "nearestNeighbor",
    "traversabilityScope", "filterScope", "shortestPathNetworkAttributeName",
}


def check(req: dict) -> list[str]:
    problems = []
    tt = req.get("traceType")
    if tt not in TRACE_TYPES:
        problems.append(f"traceType {tt!r} is not one of {sorted(TRACE_TYPES)}")
    locs = req.get("traceLocations", [])
    if isinstance(locs, str):
        locs = json.loads(locs)
    cfg = req.get("traceConfiguration", {}) or {}
    if isinstance(cfg, str):
        cfg = json.loads(cfg)
    has_named = bool(req.get("traceConfigurationGlobalId"))

    starts = [l for l in locs if l.get("traceLocationType") == "startingPoint"]
    for i, l in enumerate(locs):
        if l.get("traceLocationType") not in ("startingPoint", "barrier"):
            problems.append(f"traceLocations[{i}]: traceLocationType must be startingPoint or barrier")
        if not l.get("globalId"):
            problems.append(f"traceLocations[{i}]: missing globalId")
        if "terminalId" not in l and "percentAlong" not in l:
            problems.append(f"traceLocations[{i}] ({l.get('globalId')}): needs terminalId (junction) or "
                            "percentAlong (edge) — the service silently ignores it otherwise")
        pa = l.get("percentAlong")
        if pa is not None and not 0 <= float(pa) <= 1:
            problems.append(f"traceLocations[{i}]: percentAlong must be 0-1")

    if tt == "subnetwork":
        if not has_named and not (cfg.get("domainNetworkName") and cfg.get("tierName")):
            problems.append("subnetwork trace: set domainNetworkName and tierName in traceConfiguration")
        if cfg.get("subnetworkName") and locs:
            problems.append("subnetwork trace by subnetworkName: traceLocations should be []")
        if not cfg.get("subnetworkName") and not starts:
            problems.append("subnetwork trace: give subnetworkName or a starting point")
    elif tt and not starts:
        problems.append(f"{tt} trace has no starting points")
    if tt == "shortestPath":
        if len(starts) != 2:
            problems.append("shortestPath needs exactly two starting points")
        if not has_named and not cfg.get("shortestPathNetworkAttributeName"):
            problems.append("shortestPath: set shortestPathNetworkAttributeName")
    if tt in ("upstream", "downstream", "subnetworkController", "isolation", "subnetwork") \
            and not has_named and not (cfg.get("domainNetworkName") and cfg.get("tierName")):
        problems.append(f"{tt} trace: domainNetworkName and tierName are normally required")

    for k in cfg:
        if k not in CONFIG_KEYS:
            problems.append(f"traceConfiguration: unknown key {k!r} (typo? check rest-api/08)")

    def check_conditions(key, items, need_type=True):
        for j, c in enumerate(items or []):
            where = f"{key}[{j}]"
            if c.get("operator") not in OPERATORS:
                problems.append(f"{where}: operator {c.get('operator')!r} not valid")
            if need_type and "type" in c and c["type"] not in ("networkAttribute", "category"):
                problems.append(f"{where}: type must be networkAttribute or category")
            if "value" in c and not isinstance(c["value"], str):
                problems.append(f"{where}: value should be a string — Esri's schema types it as <string> (got {c['value']!r})")
            if "functionType" in c and c["functionType"] not in FUNCTION_TYPES:
                problems.append(f"{where}: functionType {c['functionType']!r} not valid")

    for key in ("conditionBarriers", "filterBarriers", "outputConditions"):
        check_conditions(key, cfg.get(key))
    for key in ("functionBarriers", "filterFunctionBarriers"):
        check_conditions(key, cfg.get(key), need_type=False)
    for j, f in enumerate(cfg.get("functions") or []):
        if f.get("functionType") not in FUNCTION_TYPES:
            problems.append(f"functions[{j}]: functionType {f.get('functionType')!r} not valid")
        check_conditions(f"functions[{j}].conditions", f.get("conditions"))
    for j, p in enumerate(cfg.get("propagators") or []):
        if p.get("propagatorFunctionType") not in ("bitwiseAnd", "min", "max"):
            problems.append(f"propagators[{j}]: propagatorFunctionType must be bitwiseAnd, min or max")
        check_conditions(f"propagators[{j}]", [p], need_type=False)
    for key in ("traversabilityScope", "filterScope"):
        if key in cfg and cfg[key] not in SCOPES:
            problems.append(f"{key} must be one of {sorted(SCOPES)}")
    return problems


def parse_loc(spec: str, kind: str) -> dict:
    gid, _, rest = spec.partition(":")
    loc = {"traceLocationType": kind, "globalId": gid}
    for part in filter(None, rest.split(",")):
        k, _, v = part.partition("=")
        if k == "terminal":
            loc["terminalId"] = int(v)
        elif k == "along":
            loc["percentAlong"] = float(v)
        elif k == "filter":
            loc["isFilterBarrier"] = v.lower() == "true"
    return loc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check")
    ap.add_argument("--type")
    ap.add_argument("--start", action="append", default=[])
    ap.add_argument("--barrier", action="append", default=[])
    ap.add_argument("--config")
    ap.add_argument("--named-config")
    ap.add_argument("--version", default="sde.DEFAULT")
    a = ap.parse_args()

    if a.check:
        req = json.load(open(a.check))
    else:
        req = {
            "f": "json",
            "gdbVersion": a.version,
            "traceType": a.type,
            "traceLocations": [parse_loc(s, "startingPoint") for s in a.start]
                              + [parse_loc(b, "barrier") for b in a.barrier],
            "resultTypes": [{"type": "elements", "includeGeometry": False,
                             "includePropagatedValues": False, "includeDomainDescriptions": True}],
        }
        if a.config:
            req["traceConfiguration"] = json.load(open(a.config))
        if a.named_config:
            req["traceConfigurationGlobalId"] = a.named_config

    problems = check(req)
    if problems:
        print("PROBLEMS:")
        for p in problems:
            print(" -", p)
    else:
        print("OK: no problems found")
    if not a.check:
        print("\nForm parameters for POST .../UtilityNetworkServer/trace:")
        for k, v in req.items():
            print(f"{k}={json.dumps(v) if isinstance(v, (dict, list)) else v}")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
