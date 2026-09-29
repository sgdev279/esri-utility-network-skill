#!/usr/bin/env python3
"""
Utility Network MCP server — a starting template.

Exposes an Esri ArcGIS Utility Network (enterprise deployment, published as a
feature service with the Utility Network capability) to any MCP client
(Claude Desktop, Claude Code, VS Code, Copilot, ...) as a small set of
well-scoped tools.

Design choices (see references/mcp/03-building-a-utility-network-mcp-server.md):
  * Talks to UtilityNetworkServer + FeatureServer REST directly, so it works
    against any Enterprise version with UN services, with or without Esri's
    own MCP overlay.
  * Read-only by default. Write tools (validate topology, update subnetwork)
    only register when UN_ALLOW_WRITES=true, and each call must also pass
    confirm=True, which pushes the agent to get a human "yes" first.
  * Summarises large results (traces can return 100k+ elements) instead of
    streaming them into the model's context.

Configuration (environment variables):
  UN_FEATURE_SERVICE_URL  https://host/server/rest/services/<Svc>/FeatureServer   (required)
  UN_TOKEN                a pre-issued token, OR
  UN_PORTAL_URL + UN_USERNAME + UN_PASSWORD      -> generateToken, OR
  UN_PORTAL_URL + UN_CLIENT_ID + UN_CLIENT_SECRET -> OAuth2 client_credentials
  UN_DEFAULT_VERSION      default gdbVersion for reads (default: sde.DEFAULT)
  UN_ALLOW_WRITES         "true" to register write tools (default: false)
  UN_MAX_IDS              max globalIds returned per group in summaries (default: 25)
  UN_ASSET_ID_FIELD       field matched by find_features(asset_id=...) (default: ASSETID)
  UN_VERIFY_TLS           "false" to skip TLS verification (lab use only)

Run:   python un_mcp_server.py            (stdio transport)
Test:  python un_mcp_server.py --selftest (offline checks of the pure helpers)

Requires: pip install "mcp[cli]<2" requests
"""
from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter, defaultdict
from typing import Any

# ---------------------------------------------------------------------------
# Pure helpers (no network) — unit-tested by --selftest
# ---------------------------------------------------------------------------

TRACE_TYPES = {
    "connected", "subnetwork", "subnetworkController", "upstream",
    "downstream", "loops", "shortestPath", "isolation",
}

DIRTY_STATUS_BITS = [
    (1, "feature modified (inserted/updated)"),
    (2, "feature deleted"),
    (4, "associated objects modified"),
    (8, "feature error"),
    (16, "object error"),
    (32, "subnetwork error"),
]


def decode_dirty_status(status: int) -> list[str]:
    """Decode the dirty-area Status bitmask. 0 means topology is disabled."""
    if status == 0:
        return ["network topology disabled"]
    return [label for bit, label in DIRTY_STATUS_BITS if status & bit]


DIRTY_EDIT_BITS = 1 | 2 | 4
DIRTY_ERROR_BITS = 8 | 16 | 32


def classify_dirty_status(status: int) -> dict:
    """Decode Status and say what Validate Network Topology will do with it.

    Esri: validate only evaluates dirty areas that carry an edit bit (1, 2, 4).
    Error-only dirty areas (8, 16, 32 or sums such as 40) are ignored; the
    feature (or rule / subnetwork definition) has to be edited to fix them.
    """
    meanings = decode_dirty_status(status)
    if status == 0:
        return {"meaning": meanings, "kind": "topology disabled", "validateEvaluates": False,
                "next": "Enable network topology; Status is meaningless while it is off."}
    has_edit = bool(status & DIRTY_EDIT_BITS)
    has_error = bool(status & DIRTY_ERROR_BITS)
    if has_error and not has_edit:
        nxt = ("Validate ignores this row. Fix the cause by editing the feature, rule or "
               "subnetwork definition, then validate.")
        if status & 32:
            nxt += " Then run Update Subnetwork; the subnetwork stays Invalid until it updates cleanly."
        return {"meaning": meanings, "kind": "error only", "validateEvaluates": False, "next": nxt}
    if has_error:
        return {"meaning": meanings, "kind": "edit + error", "validateEvaluates": True,
                "next": "Validate evaluates it; if the feature still violates a rule it becomes error-only."}
    return {"meaning": meanings, "kind": "edit only", "validateEvaluates": True,
            "next": "No error. Validate network topology to clear it."}


def asset_names_from_layer(layer: dict) -> dict:
    """{(assetGroupCode, assetTypeCode): (assetGroupName, assetTypeName)} from a
    feature layer's `types` (asset groups are subtypes; asset types are the
    coded values of each subtype's ASSETTYPE domain)."""
    out: dict = {}
    for t in layer.get("types", []) or []:
        gcode, gname = t.get("id"), t.get("name")
        for fname, dom in (t.get("domains") or {}).items():
            if fname.lower() != "assettype":
                continue
            for cv in (dom or {}).get("codedValues", []) or []:
                out[(gcode, cv.get("code"))] = (gname, cv.get("name"))
    return out


def feature_service_to_un_server(url: str) -> str:
    url = url.rstrip("/")
    if not url.endswith("/FeatureServer"):
        raise ValueError("UN_FEATURE_SERVICE_URL must end with /FeatureServer")
    return url[: -len("FeatureServer")] + "UtilityNetworkServer"


def build_trace_locations(starting_points: list[dict], barriers: list[dict] | None) -> list[dict]:
    """Normalise agent-supplied locations into the REST traceLocations schema.

    Each item: {"globalId": "{...}", "terminalId": int?, "percentAlong": float?,
    "isFilterBarrier": bool?}. Junctions need terminalId, edges need
    percentAlong — the service silently IGNORES a location missing its
    required property, so we reject it here instead.
    """
    out = []
    for kind, items in (("startingPoint", starting_points or []), ("barrier", barriers or [])):
        for i, loc in enumerate(items):
            gid = loc.get("globalId") or loc.get("global_id")
            if not gid:
                raise ValueError(f"{kind} #{i}: globalId is required")
            has_term = loc.get("terminalId") is not None
            has_pct = loc.get("percentAlong") is not None
            if not (has_term or has_pct):
                raise ValueError(
                    f"{kind} #{i} ({gid}): give terminalId for a junction/device "
                    "or percentAlong (0-1) for a line; the service silently skips "
                    "locations missing both.")
            if has_pct and not 0.0 <= float(loc["percentAlong"]) <= 1.0:
                raise ValueError(f"{kind} #{i}: percentAlong must be between 0 and 1")
            item = {"traceLocationType": kind, "globalId": gid}
            if has_term:
                item["terminalId"] = int(loc["terminalId"])
            if has_pct:
                item["percentAlong"] = float(loc["percentAlong"])
            if kind == "barrier" and loc.get("isFilterBarrier"):
                item["isFilterBarrier"] = True
            out.append(item)
    return out


def summarize_trace_result(result: dict, source_names: dict[int, str] | None = None,
                           max_ids: int = 25, asset_names: dict | None = None) -> dict:
    """Condense a trace response into counts + a capped sample of globalIds.

    Trace elements carry codes only (networkSourceId, assetGroupCode,
    assetTypeCode). Pass `asset_names` ({(source, group, type): (groupName,
    typeName)}) to add readable names alongside the codes."""
    source_names = source_names or {}
    asset_names = asset_names or {}
    tr = result.get("traceResults", result)
    elements = tr.get("elements", []) or []
    groups: dict[tuple, list[str]] = defaultdict(list)
    for e in elements:
        key = (e.get("networkSourceId"), e.get("assetGroupCode"), e.get("assetTypeCode"))
        groups[key].append(e.get("globalId"))
    by_group = []
    for (src, ag, at), gids in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        row = {
            "networkSource": source_names.get(src, src),
            "assetGroupCode": ag,
            "assetTypeCode": at,
            "count": len(gids),
            "sampleGlobalIds": gids[:max_ids],
            "truncated": len(gids) > max_ids,
        }
        names = asset_names.get((src, ag, at))
        if names:
            row["assetGroup"], row["assetType"] = names
        by_group.append(row)
    summary = {
        "success": result.get("success", True),
        "totalElements": len(elements),
        "byAssetGroupType": by_group,
    }
    for key in ("globalFunctionResults", "kFeaturesForKNNFound", "startingPointsIgnored", "warnings"):
        if key in tr and tr[key] not in (None, [], False):
            summary[key] = tr[key]
    if tr.get("startingPointsIgnored"):
        summary["hint"] = ("Some starting points were ignored — check terminalId/percentAlong "
                           "and that the features are in the traced domain network.")
    return summary


def find_key(obj: Any, name: str) -> Any:
    """Depth-first search for the first value stored under key `name`."""
    if isinstance(obj, dict):
        if name in obj:
            return obj[name]
        for v in obj.values():
            r = find_key(v, name)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = find_key(v, name)
            if r is not None:
                return r
    return None


def pick_system_layer(system_layers: dict, *needles: str) -> int | None:
    """systemLayers key names vary slightly by release; match by substring."""
    for k, v in (system_layers or {}).items():
        lk = k.lower()
        if all(n in lk for n in needles) and isinstance(v, int):
            return v
    return None


def check_write_allowed(confirm: bool, gdb_version: str) -> None:
    if os.environ.get("UN_ALLOW_WRITES", "false").lower() != "true":
        raise PermissionError("Write tools are disabled (set UN_ALLOW_WRITES=true on the server).")
    if not confirm:
        raise PermissionError(
            f"This changes data in version '{gdb_version}'. Ask the user to confirm, "
            "then call again with confirm=true.")


# ---------------------------------------------------------------------------
# REST client
# ---------------------------------------------------------------------------

class UNClient:
    def __init__(self) -> None:
        import requests  # imported lazily so --selftest runs without it
        self.requests = requests
        self.fs_url = os.environ["UN_FEATURE_SERVICE_URL"].rstrip("/")
        self.un_url = feature_service_to_un_server(self.fs_url)
        self.verify = os.environ.get("UN_VERIFY_TLS", "true").lower() != "false"
        self.default_version = os.environ.get("UN_DEFAULT_VERSION", "sde.DEFAULT")
        self._token: str | None = os.environ.get("UN_TOKEN")
        self._token_expiry = float("inf") if self._token else 0.0
        self._un_layer: dict | None = None

    # -- auth --------------------------------------------------------------
    def token(self) -> str | None:
        if self._token and time.time() < self._token_expiry - 60:
            return self._token
        portal = os.environ.get("UN_PORTAL_URL", "").rstrip("/")
        if not portal:
            return self._token  # anonymous / pre-issued
        if os.environ.get("UN_CLIENT_ID"):
            r = self.requests.post(f"{portal}/sharing/rest/oauth2/token", data={
                "client_id": os.environ["UN_CLIENT_ID"],
                "client_secret": os.environ["UN_CLIENT_SECRET"],
                "grant_type": "client_credentials", "f": "json"}, verify=self.verify, timeout=60)
            j = r.json()
            self._token = j["access_token"]
            self._token_expiry = time.time() + int(j.get("expires_in", 3600))
        else:
            r = self.requests.post(f"{portal}/sharing/rest/generateToken", data={
                "username": os.environ["UN_USERNAME"], "password": os.environ["UN_PASSWORD"],
                "referer": portal, "expiration": 60, "f": "json"}, verify=self.verify, timeout=60)
            j = r.json()
            if "token" not in j:
                raise RuntimeError(f"generateToken failed: {j.get('error')}")
            self._token = j["token"]
            self._token_expiry = j.get("expires", 0) / 1000.0
        return self._token

    def call(self, url: str, params: dict | None = None, post: bool = True) -> dict:
        data = {"f": "json"}
        for k, v in (params or {}).items():
            if v is None:
                continue
            data[k] = json.dumps(v) if isinstance(v, (dict, list, bool)) else v
        tok = self.token()
        if tok:
            data["token"] = tok
        fn = self.requests.post if post else self.requests.get
        kw = {"data": data} if post else {"params": data}
        r = fn(url, verify=self.verify, timeout=600, **kw)
        r.raise_for_status()
        j = r.json()
        if isinstance(j, dict) and j.get("error"):
            raise RuntimeError(json.dumps(j["error"]))
        return j

    # -- discovery ---------------------------------------------------------
    def un_layer(self) -> dict:
        if self._un_layer is None:
            fs = self.call(self.fs_url, post=False)
            lid = find_key(fs, "utilityNetworkLayerId")
            if lid is None:
                raise RuntimeError("No utilityNetworkLayerId on this FeatureServer — "
                                   "is the Utility Network capability published?")
            layer = self.call(f"{self.fs_url}/{lid}", post=False)
            layer["_layerId"] = lid
            self._un_layer = layer
        return self._un_layer

    def system_layer_id(self, *needles: str) -> int:
        lid = pick_system_layer(self.un_layer().get("systemLayers", {}), *needles)
        if lid is None:
            raise RuntimeError(f"System layer matching {needles} not found in systemLayers")
        return lid

    def source_names(self) -> dict[int, str]:
        de = self.data_element()
        names = {}
        for dn in de.get("domainNetworks", []) or []:
            for key in ("junctionSources", "edgeSources"):
                for s in dn.get(key, []) or []:
                    names[s.get("sourceId")] = s.get("sourceName") or s.get("name")
        return names

    def feature_layers(self) -> list[dict]:
        """Layers and tables listed on the FeatureServer root ({id, name})."""
        fs = self.call(self.fs_url, post=False)
        return [{"id": l["id"], "name": l.get("name", "")}
                for k in ("layers", "tables") for l in fs.get(k, []) or [] if "id" in l]

    def asset_name_map(self) -> dict:
        """Best effort: {(networkSourceId, group, type): (groupName, typeName)}.
        Needs each source's layerId in the data element; returns {} if absent."""
        if getattr(self, "_asset_names", None) is not None:
            return self._asset_names
        out: dict = {}
        try:
            de = self.data_element()
            for dn in de.get("domainNetworks", []) or []:
                for key in ("junctionSources", "edgeSources"):
                    for src in dn.get(key, []) or []:
                        sid, lid = src.get("sourceId"), src.get("layerId")
                        if sid is None or lid is None:
                            continue
                        layer = self.call(f"{self.fs_url}/{lid}", post=False)
                        for (g, t), names in asset_names_from_layer(layer).items():
                            out[(sid, g, t)] = names
        except Exception:
            out = {}
        self._asset_names = out
        return out

    def data_element(self) -> dict:
        lid = self.un_layer()["_layerId"]
        j = self.call(f"{self.fs_url}/queryDataElements", {"layers": [lid]}, post=False)
        layers = j.get("layerDataElements", [])
        return layers[0].get("dataElement", {}) if layers else {}


# ---------------------------------------------------------------------------
# MCP tool definitions
# ---------------------------------------------------------------------------

def build_server():
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("utility-network")
    client = UNClient()
    max_ids = int(os.environ.get("UN_MAX_IDS", "25"))

    @mcp.tool()
    def describe_network() -> dict:
        """Summarise the utility network's configuration: domain networks, tiers,
        subnetwork controllers' tiers, network attributes, categories and the
        system layer IDs. Call this first — other tools need these names."""
        de = client.data_element()
        dns = []
        for dn in de.get("domainNetworks", []) or []:
            dns.append({
                "name": dn.get("domainNetworkName"),
                "tierDefinition": dn.get("tierDefinition"),
                "subnetworkControllerType": dn.get("subnetworkControllerType"),
                "tiers": [t.get("name") for t in dn.get("tiers", []) or []],
                "sources": [s.get("name") for k in ("junctionSources", "edgeSources")
                            for s in dn.get(k, []) or []],
            })
        return {
            "utilityNetworkLayerId": client.un_layer()["_layerId"],
            "schemaGeneration": de.get("schemaGeneration"),
            "domainNetworks": dns,
            "networkAttributes": [a.get("name") for a in de.get("networkAttributes", []) or []],
            "categories": [c.get("name") for c in de.get("categories", []) or []],
            "systemLayers": client.un_layer().get("systemLayers", {}),
        }

    @mcp.tool()
    def list_trace_configurations() -> dict:
        """List named trace configurations stored in the service (name, globalId,
        creator). Prefer running one of these over hand-building a configuration."""
        return client.call(f"{client.un_url}/traceConfigurations/query", {})

    @mcp.tool()
    def trace(trace_type: str,
              starting_points: list[dict],
              barriers: list[dict] | None = None,
              named_trace_configuration_global_id: str | None = None,
              trace_configuration: dict | None = None,
              gdb_version: str | None = None,
              moment_epoch_ms: int | None = None) -> dict:
        """Run a utility network trace and return a SUMMARY (counts by asset group/
        type plus sample globalIds), never the full element list.

        trace_type: connected | subnetwork | subnetworkController | upstream |
          downstream | loops | shortestPath | isolation.
        starting_points / barriers: [{"globalId": "{...}", "terminalId": 1}] for
          devices/junctions, or [{"globalId": "{...}", "percentAlong": 0.5}] for lines.
        Supply EITHER a named configuration globalId (preferred) OR a
        trace_configuration object (REST traceConfiguration schema). For
        subnetwork traces, domainNetworkName/tierName/subnetworkName normally
        need to be set in trace_configuration.
        """
        if trace_type not in TRACE_TYPES:
            raise ValueError(f"trace_type must be one of {sorted(TRACE_TYPES)}")
        params = {
            "traceType": trace_type,
            "traceLocations": build_trace_locations(starting_points, barriers),
            "gdbVersion": gdb_version or client.default_version,
            "moment": moment_epoch_ms,
            "resultTypes": [{"type": "elements", "includeGeometry": False,
                             "includePropagatedValues": False, "includeDomainDescriptions": True}],
        }
        if named_trace_configuration_global_id:
            params["traceConfigurationGlobalId"] = named_trace_configuration_global_id
        if trace_configuration:
            params["traceConfiguration"] = trace_configuration
        raw = client.call(f"{client.un_url}/trace", params)
        return summarize_trace_result(raw, client.source_names(), max_ids, client.asset_name_map())

    @mcp.tool()
    def query_associations(elements: list[dict], types: list[str] | None = None,
                           gdb_version: str | None = None) -> dict:
        """Return associations for specific network elements.
        elements: [{"networkSourceId": 7, "globalId": "{...}", "terminalId": 1}]
        types (optional): attachment, containment, junctionJunctionConnectivity,
          junctionEdgeFromConnectivity, junctionMidspanConnectivity,
          junctionEdgeToConnectivity. Get networkSourceId from describe_network."""
        return client.call(f"{client.un_url}/associations/query", {
            "elements": elements, "types": types,
            "gdbVersion": gdb_version or client.default_version})

    @mcp.tool()
    def query_subnetworks(where: str = "1=1", out_fields: str = "*",
                          gdb_version: str | None = None, max_records: int = 200) -> dict:
        """Query the Subnetworks system table, for example
        where="SUBNETWORKNAME='FDR-12'". The ISDIRTY field holds clean / dirty /
        invalid, but Esri's table page does not list the stored codes: read a few
        rows and compare with the status Pro shows before filtering on a number."""
        lid = client.system_layer_id("subnetwork")
        return client.call(f"{client.fs_url}/{lid}/query", {
            "where": where, "outFields": out_fields, "returnGeometry": False,
            "resultRecordCount": max_records,
            "gdbVersion": gdb_version or client.default_version}, post=False)

    @mcp.tool()
    def dirty_area_summary(gdb_version: str | None = None) -> dict:
        """Count dirty areas grouped by Status and decode each Status bitmask
        (edits pending validation vs. feature/object/subnetwork errors), with
        what Validate will do about each and the next action."""
        lid = client.system_layer_id("dirty")
        j = client.call(f"{client.fs_url}/{lid}/query", {
            "where": "1=1", "groupByFieldsForStatistics": "STATUS",
            "outStatistics": [{"statisticType": "count", "onStatisticField": "OBJECTID",
                               "outStatisticFieldName": "n"}],
            "returnGeometry": False,
            "gdbVersion": gdb_version or client.default_version}, post=False)
        rows = []
        for f in j.get("features", []):
            a = {k.lower(): v for k, v in f["attributes"].items()}
            s = int(a.get("status") or 0)
            rows.append({"status": s, "count": a.get("n"), **classify_dirty_status(s)})
        rows.sort(key=lambda r: r["status"])
        total = sum(r["count"] or 0 for r in rows)
        errors = sum(r["count"] or 0 for r in rows if r["status"] & DIRTY_ERROR_BITS)
        stuck = sum(r["count"] or 0 for r in rows if r["kind"] == "error only")
        return {"totalDirtyAreas": total, "withErrors": errors,
                "errorOnlyIgnoredByValidate": stuck, "byStatus": rows}

    @mcp.tool()
    def find_features(asset_id: str | None = None, where: str | None = None,
                      layer_name: str | None = None, gdb_version: str | None = None,
                      max_records: int = 25) -> dict:
        """Find features by asset ID (or a SQL where clause) and return the
        globalId, objectId and asset group / asset type NAMES, so a person can
        say "CB-1042" instead of a GUID. Use the result's globalId in trace.

        asset_id: matched against the field named by UN_ASSET_ID_FIELD
          (default ASSETID). where: an alternative SQL filter. layer_name:
          restrict to layers whose name contains this text (recommended:
          searching every layer is slow). A device still needs a terminalId to
          start a trace; ask the user or use a named trace configuration."""
        if not asset_id and not where:
            raise ValueError("Give asset_id or where")
        field = os.environ.get("UN_ASSET_ID_FIELD", "ASSETID")
        clause = where or f"{field} = '{str(asset_id).replace(chr(39), chr(39) * 2)}'"
        un_lid = client.un_layer()["_layerId"]
        sys_ids = {v for v in client.un_layer().get("systemLayers", {}).values() if isinstance(v, int)}
        layers = [l for l in client.feature_layers()
                  if l["id"] != un_lid and l["id"] not in sys_ids
                  and (not layer_name or layer_name.lower() in l["name"].lower())][:30]
        found, skipped = [], []
        for l in layers:
            try:
                meta = client.call(f"{client.fs_url}/{l['id']}", post=False)
                names = asset_names_from_layer(meta)
                j = client.call(f"{client.fs_url}/{l['id']}/query", {
                    "where": clause, "outFields": "*", "returnGeometry": False,
                    "resultRecordCount": max_records,
                    "gdbVersion": gdb_version or client.default_version}, post=False)
            except Exception as e:  # layer without the field, no access, etc.
                skipped.append({"layer": l["name"], "reason": str(e)[:120]})
                continue
            for f in j.get("features", []) or []:
                a = {k.upper(): v for k, v in f.get("attributes", {}).items()}
                g, t = a.get("ASSETGROUP"), a.get("ASSETTYPE")
                gname, tname = names.get((g, t), (None, None))
                found.append({"layer": l["name"], "layerId": l["id"],
                              "globalId": a.get("GLOBALID"), "objectId": a.get("OBJECTID"),
                              "assetGroupCode": g, "assetTypeCode": t,
                              "assetGroup": gname, "assetType": tname,
                              "assetId": a.get(field.upper())})
        return {"query": clause, "matches": found[:max_records], "layersSearched": len(layers),
                "layersSkipped": skipped}

    @mcp.tool()
    def network_moments() -> dict:
        """When topology was first and last enabled, and whether it is valid."""
        return client.call(f"{client.un_url}/queryNetworkMoments", {
            "momentsToReturn": ["enableTopology", "initialEnableTopology"]})

    @mcp.tool()
    def job_status(status_url: str) -> dict:
        """Poll an async job's statusUrl (from async=true operations)."""
        if not status_url.startswith(client.un_url.rsplit("/rest/", 1)[0]):
            raise ValueError("status_url must belong to the configured server")
        return client.call(status_url, {}, post=False)

    if os.environ.get("UN_ALLOW_WRITES", "false").lower() == "true":

        @mcp.tool()
        def validate_network_topology(xmin: float, ymin: float, xmax: float, ymax: float,
                                      wkid: int, gdb_version: str | None = None,
                                      session_id: str | None = None,
                                      validation_type: str = "normal",
                                      confirm: bool = False) -> dict:
            """WRITE: validate topology inside an extent (clears dirty areas, may
            create error features). validation_type: normal | rebuild | forceRebuild.
            Needs confirm=true after the user agrees. session_id is required
            for a named version."""
            if validation_type not in ("normal", "rebuild", "forceRebuild"):
                raise ValueError("validation_type must be normal, rebuild or forceRebuild")
            v = gdb_version or client.default_version
            check_write_allowed(confirm, v)
            return client.call(f"{client.un_url}/validateNetworkTopology", {
                "gdbVersion": v, "sessionID": session_id, "validationType": validation_type,
                "validateArea": {"xmin": xmin, "ymin": ymin, "xmax": xmax, "ymax": ymax,
                                 "spatialReference": {"wkid": wkid}},
                "async": True})

        @mcp.tool()
        def update_subnetwork(domain_network_name: str, tier_name: str,
                              subnetwork_name: str | None = None,
                              all_subnetworks_in_tier: bool = False,
                              continue_on_failure: bool = False,
                              gdb_version: str | None = None,
                              session_id: str | None = None,
                              confirm: bool = False) -> dict:
            """WRITE: run Update Subnetwork (async). Give subnetwork_name OR
            all_subnetworks_in_tier=true. Needs confirm=true after the user agrees.
            Returns a statusUrl — poll it with job_status."""
            if not subnetwork_name and not all_subnetworks_in_tier:
                raise ValueError("Give subnetwork_name or set all_subnetworks_in_tier=true")
            v = gdb_version or client.default_version
            check_write_allowed(confirm, v)
            return client.call(f"{client.un_url}/updateSubnetwork", {
                "gdbVersion": v, "sessionId": session_id,
                "domainNetworkName": domain_network_name, "tierName": tier_name,
                "subnetworkName": subnetwork_name,
                "allSubnetworksInTier": all_subnetworks_in_tier,
                "continueOnFailure": continue_on_failure, "async": True})

    return mcp


# ---------------------------------------------------------------------------
# Self-test (offline)
# ---------------------------------------------------------------------------

def _selftest() -> None:
    assert decode_dirty_status(0) == ["network topology disabled"]
    assert decode_dirty_status(10) == ["feature deleted", "feature error"]
    assert feature_service_to_un_server(
        "https://h/server/rest/services/Elec/FeatureServer/") == \
        "https://h/server/rest/services/Elec/UtilityNetworkServer"
    locs = build_trace_locations([{"globalId": "{A}", "terminalId": 1}],
                                 [{"globalId": "{B}", "percentAlong": 0.5, "isFilterBarrier": True}])
    assert locs[0] == {"traceLocationType": "startingPoint", "globalId": "{A}", "terminalId": 1}
    assert locs[1]["isFilterBarrier"] is True and locs[1]["percentAlong"] == 0.5
    for bad in ([{"globalId": "{A}"}], [{"terminalId": 1}], [{"globalId": "{A}", "percentAlong": 2}]):
        try:
            build_trace_locations(bad, None)
            raise AssertionError("expected ValueError")
        except ValueError:
            pass
    fake = {"success": True, "traceResults": {"elements": [
        {"networkSourceId": 5, "assetGroupCode": 1, "assetTypeCode": 2, "globalId": f"{{{i}}}"}
        for i in range(30)] + [{"networkSourceId": 7, "assetGroupCode": 3, "assetTypeCode": 1,
                                "globalId": "{x}"}], "startingPointsIgnored": True}}
    s = summarize_trace_result(fake, {5: "ElectricDevice"}, max_ids=10)
    assert s["totalElements"] == 31 and s["byAssetGroupType"][0]["count"] == 30
    assert s["byAssetGroupType"][0]["networkSource"] == "ElectricDevice"
    assert s["byAssetGroupType"][0]["truncated"] and len(s["byAssetGroupType"][0]["sampleGlobalIds"]) == 10
    assert "hint" in s
    assert find_key({"a": [{"controllerDatasetLayers": {"utilityNetworkLayerId": 15}}]},
                    "utilityNetworkLayerId") == 15
    assert pick_system_layer({"dirtyAreasLayerId": 3, "subnetworksTableId": 9}, "subnetwork") == 9
    k = classify_dirty_status
    assert k(1)["kind"] == "edit only" and k(1)["validateEvaluates"]
    assert k(9)["kind"] == "edit + error" and k(9)["validateEvaluates"]
    assert k(8)["kind"] == "error only" and not k(8)["validateEvaluates"]
    assert k(40)["kind"] == "error only" and "Update Subnetwork" in k(40)["next"]
    assert k(0)["kind"] == "topology disabled"
    layer = {"types": [{"id": 4, "name": "Breaker", "domains": {
        "ASSETTYPE": {"codedValues": [{"name": "Feeder Breaker", "code": 21}]}}}]}
    assert asset_names_from_layer(layer) == {(4, 21): ("Breaker", "Feeder Breaker")}
    named = summarize_trace_result(fake, {5: "ElectricDevice"}, asset_names={(5, 1, 2): ("Fuse", "Cutout")})
    assert named["byAssetGroupType"][0]["assetGroup"] == "Fuse"
    os.environ["UN_ALLOW_WRITES"] = "false"
    try:
        check_write_allowed(True, "sde.DEFAULT")
        raise AssertionError("expected PermissionError")
    except PermissionError:
        pass
    os.environ["UN_ALLOW_WRITES"] = "true"
    try:
        check_write_allowed(False, "sde.DEFAULT")
        raise AssertionError("expected PermissionError")
    except PermissionError:
        pass
    check_write_allowed(True, "sde.DEFAULT")
    print("selftest ok")


def main() -> None:
    """Console entry point: `utility-network-mcp` (stdio) or `--selftest`."""
    if "--selftest" in sys.argv:
        _selftest()
    else:
        build_server().run()


if __name__ == "__main__":
    main()
