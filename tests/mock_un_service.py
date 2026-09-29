"""A tiny fake ArcGIS Enterprise utility network service for tests.

It mimics only what the MCP server calls: FeatureServer (root, layer, query,
queryDataElements), UtilityNetworkServer (trace, associations/query,
traceConfigurations/query, queryNetworkMoments, validateNetworkTopology,
updateSubnetwork) and the portal OAuth2 token endpoint. Response shapes follow
Esri's REST docs where they are documented, and standard feature-layer JSON
elsewhere. It is a stand-in, NOT a substitute for a test against a real service.
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

TOKEN = "TESTTOKEN"
SVC = "/server/rest/services/ElectricUN"

ASSET_GROUPS = [{
    "id": 4, "name": "Breaker",
    "domains": {"ASSETTYPE": {"type": "codedValue", "codedValues": [
        {"name": "Feeder Breaker", "code": 21}, {"name": "Recloser", "code": 22}]}}}]

DEVICE_ROW = {"OBJECTID": 101, "GLOBALID": "{8F2A6C1E-4B7D-4E1A-9C55-2D0F7A1B3E90}",
              "ASSETGROUP": 4, "ASSETTYPE": 21, "ASSETID": "CB-1042"}

DIRTY_ROWS = [(1, 41220), (2, 130), (8, 5), (9, 312), (40, 18)]


class Handler(BaseHTTPRequestHandler):
    server_version = "MockUN/1"

    def log_message(self, *a):  # keep test output clean
        pass

    def _params(self):
        u = urlparse(self.path)
        q = {k: v[-1] for k, v in parse_qs(u.query).items()}
        n = int(self.headers.get("Content-Length") or 0)
        if n:
            q.update({k: v[-1] for k, v in parse_qs(self.rfile.read(n).decode()).items()})
        return u.path, q

    def _send(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._handle()

    def do_POST(self):
        self._handle()

    def _handle(self):
        path, q = self._params()
        self.server.calls.append((path, q))
        if path.endswith("/sharing/rest/oauth2/token"):
            if q.get("client_id") == "cid" and q.get("client_secret") == "sec":
                return self._send({"access_token": TOKEN, "expires_in": 3600})
            return self._send({"error": {"code": 400, "message": "bad client"}})
        if q.get("token") != TOKEN:
            return self._send({"error": {"code": 498, "message": "Invalid token."}})
        if not path.startswith(SVC):
            return self._send({"error": {"code": 404, "message": "not found"}}, 404)
        rel = path[len(SVC):]

        if rel == "/FeatureServer":
            return self._send({
                "layers": [{"id": 1, "name": "Electric Device"}, {"id": 2, "name": "Electric Line"},
                           {"id": 9, "name": "Electric Utility Network"}],
                "tables": [{"id": 20, "name": "Dirty Areas"}, {"id": 21, "name": "Subnetworks"}],
                "controllerDatasetLayers": {"utilityNetworkLayerId": 9}})
        if rel == "/FeatureServer/9":
            return self._send({"name": "Electric Utility Network", "systemLayers": {
                "dirtyAreasLayerId": 20, "subnetworksTableId": 21, "associationsTableId": 22}})
        if rel == "/FeatureServer/1":
            return self._send({"name": "Electric Device", "types": ASSET_GROUPS})
        if rel == "/FeatureServer/2":
            return self._send({"name": "Electric Line", "types": []})
        if rel == "/FeatureServer/queryDataElements":
            return self._send({"layerDataElements": [{"layerId": 9, "dataElement": {
                "schemaGeneration": 7,
                "domainNetworks": [{
                    "domainNetworkName": "ElectricDistribution", "tierDefinition": "hierarchical",
                    "subnetworkControllerType": "sourceDriven",
                    "tiers": [{"name": "Medium Voltage"}],
                    "junctionSources": [{"sourceId": 5, "layerId": 1, "name": "ElectricDevice"}],
                    "edgeSources": [{"sourceId": 6, "layerId": 2, "name": "ElectricLine"}]}],
                "networkAttributes": [{"name": "Phases Normal"}],
                "categories": [{"name": "Protective"}]}}]})
        if rel == "/FeatureServer/1/query":
            w = q.get("where", "")
            rows = [DEVICE_ROW] if "CB-1042" in w else []
            return self._send({"features": [{"attributes": r} for r in rows]})
        if rel == "/FeatureServer/2/query":  # no ASSETID field on lines
            return self._send({"error": {"code": 400, "message": "Invalid field: ASSETID"}})
        if rel == "/FeatureServer/20/query":
            return self._send({"features": [{"attributes": {"STATUS": s, "n": n}} for s, n in DIRTY_ROWS]})
        if rel == "/FeatureServer/21/query":
            return self._send({"features": [
                {"attributes": {"SUBNETWORKNAME": "FDR-12", "TIERNAME": "Medium Voltage", "ISDIRTY": 1}}]})
        if rel == "/UtilityNetworkServer/trace":
            els = [{"networkSourceId": 5, "globalId": "{D%d}" % i, "objectId": i, "terminalId": 1,
                    "assetGroupCode": 4, "assetTypeCode": 22} for i in range(3)]
            els += [{"networkSourceId": 6, "globalId": "{L%d}" % i, "objectId": 50 + i,
                     "assetGroupCode": 1, "assetTypeCode": 1, "positionFrom": 0.0, "positionTo": 1.0}
                    for i in range(40)]
            return self._send({"success": True, "traceResults": {"elements": els}})
        if rel == "/UtilityNetworkServer/traceConfigurations/query":
            return self._send({"traceConfigurations": [
                {"name": "Downstream Protective", "globalId": "{11111111-1111-1111-1111-111111111111}"}]})
        if rel == "/UtilityNetworkServer/queryNetworkMoments":
            return self._send({"moments": {"enableTopology": 1700000000000}})
        if rel in ("/UtilityNetworkServer/validateNetworkTopology", "/UtilityNetworkServer/updateSubnetwork"):
            return self._send({"statusUrl": f"http://127.0.0.1:{self.server.server_port}{SVC}/jobs/1"})
        return self._send({"error": {"code": 404, "message": f"mock has no route {rel}"}}, 404)


def start():
    """Start the mock on a free port. Returns (server, base_url)."""
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    srv.calls = []
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_port}"
