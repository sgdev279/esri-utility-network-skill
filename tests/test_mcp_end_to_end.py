"""End-to-end test of the MCP server against a mock utility network service.

Runs the real tool functions through FastMCP (as an MCP client would) with the
REST calls answered by tests/mock_un_service.py. Needs: pip install "mcp<2" requests
"""
import asyncio
import importlib.util
import json
import os
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
import mock_un_service as mock  # noqa: E402

SERVER = ROOT / "mcp-server/src/utility_network_mcp/server.py"
ENV_KEYS = ("UN_FEATURE_SERVICE_URL", "UN_TOKEN", "UN_PORTAL_URL", "UN_CLIENT_ID", "UN_CLIENT_SECRET",
            "UN_ALLOW_WRITES", "UN_DEFAULT_VERSION", "UN_ASSET_ID_FIELD", "UN_USERNAME", "UN_PASSWORD")


def load_server():
    spec = importlib.util.spec_from_file_location("un_server_under_test", SERVER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def call(mcp, name, args=None):
    out = asyncio.run(mcp.call_tool(name, args or {}))
    blocks = out[0] if isinstance(out, tuple) else out
    return json.loads(blocks[0].text)


class EndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv, cls.base = mock.start()
        cls.fs_url = f"{cls.base}{mock.SVC}/FeatureServer"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def setUp(self):
        for k in ENV_KEYS:
            os.environ.pop(k, None)
        os.environ["UN_FEATURE_SERVICE_URL"] = self.fs_url
        os.environ["UN_TOKEN"] = mock.TOKEN
        self.srv.calls.clear()
        self.mod = load_server()

    def server(self):
        return self.mod.build_server()

    def tool_names(self, mcp):
        return {t.name for t in asyncio.run(mcp.list_tools())}

    # -- registration and safety ------------------------------------------
    def test_read_only_by_default(self):
        names = self.tool_names(self.server())
        self.assertIn("find_features", names)
        self.assertIn("dirty_area_summary", names)
        self.assertNotIn("validate_network_topology", names)
        self.assertNotIn("update_subnetwork", names)

    def test_write_tools_need_opt_in_and_confirmation(self):
        os.environ["UN_ALLOW_WRITES"] = "true"
        mcp = self.server()
        self.assertIn("update_subnetwork", self.tool_names(mcp))
        with self.assertRaises(Exception) as cm:
            call(mcp, "update_subnetwork", {"domain_network_name": "ElectricDistribution",
                                            "tier_name": "Medium Voltage", "subnetwork_name": "FDR-12"})
        self.assertIn("confirm", str(cm.exception).lower())
        self.assertFalse(any(p.endswith("/updateSubnetwork") for p, _ in self.srv.calls))
        r = call(mcp, "update_subnetwork", {"domain_network_name": "ElectricDistribution",
                                            "tier_name": "Medium Voltage", "subnetwork_name": "FDR-12",
                                            "confirm": True})
        self.assertIn("statusUrl", r)

    # -- discovery and reads ----------------------------------------------
    def test_describe_network(self):
        r = call(self.server(), "describe_network")
        self.assertEqual(r["utilityNetworkLayerId"], 9)
        self.assertEqual(r["schemaGeneration"], 7)
        self.assertEqual(r["domainNetworks"][0]["name"], "ElectricDistribution")
        self.assertEqual(r["systemLayers"]["dirtyAreasLayerId"], 20)

    def test_dirty_area_summary_explains_what_validate_ignores(self):
        r = call(self.server(), "dirty_area_summary")
        by = {row["status"]: row for row in r["byStatus"]}
        self.assertEqual(r["totalDirtyAreas"], 41220 + 130 + 5 + 312 + 18)
        self.assertEqual(r["withErrors"], 5 + 312 + 18)
        self.assertEqual(r["errorOnlyIgnoredByValidate"], 5 + 18)
        self.assertTrue(by[1]["validateEvaluates"])
        self.assertTrue(by[9]["validateEvaluates"])
        self.assertFalse(by[8]["validateEvaluates"])
        self.assertFalse(by[40]["validateEvaluates"])
        self.assertIn("Update Subnetwork", by[40]["next"])

    def test_query_subnetworks_uses_the_system_table(self):
        r = call(self.server(), "query_subnetworks", {"where": "ISDIRTY = 1"})
        self.assertEqual(r["features"][0]["attributes"]["SUBNETWORKNAME"], "FDR-12")
        path, q = [c for c in self.srv.calls if c[0].endswith("/FeatureServer/21/query")][-1]
        self.assertEqual(q["where"], "ISDIRTY = 1")

    # -- find by asset ID (the dispatch case) -------------------------------
    def test_find_features_by_asset_id_returns_names_and_guid(self):
        r = call(self.server(), "find_features", {"asset_id": "CB-1042"})
        self.assertEqual(len(r["matches"]), 1)
        m = r["matches"][0]
        self.assertEqual(m["globalId"], "{8F2A6C1E-4B7D-4E1A-9C55-2D0F7A1B3E90}")
        self.assertEqual((m["assetGroup"], m["assetType"]), ("Breaker", "Feeder Breaker"))
        self.assertEqual(m["layer"], "Electric Device")
        # the line layer has no ASSETID field: skipped, not fatal
        self.assertEqual([s["layer"] for s in r["layersSkipped"]], ["Electric Line"])

    def test_find_features_escapes_quotes(self):
        r = call(self.server(), "find_features", {"asset_id": "O'Brien"})
        self.assertEqual(r["query"], "ASSETID = 'O''Brien'")
        self.assertEqual(r["matches"], [])

    def test_find_features_needs_a_filter(self):
        with self.assertRaises(Exception):
            call(self.server(), "find_features", {})

    # -- trace ---------------------------------------------------------------
    def test_trace_summarises_with_names_and_sends_version(self):
        r = call(self.server(), "trace", {
            "trace_type": "downstream",
            "starting_points": [{"globalId": "{8F2A6C1E-4B7D-4E1A-9C55-2D0F7A1B3E90}", "terminalId": 2}],
            "trace_configuration": {"domainNetworkName": "ElectricDistribution", "tierName": "Medium Voltage"},
            "gdb_version": "crew1.outage"})
        self.assertEqual(r["totalElements"], 43)
        top = r["byAssetGroupType"][0]
        self.assertEqual(top["count"], 40)
        self.assertEqual(top["networkSource"], "ElectricLine")
        self.assertTrue(top["truncated"])
        dev = [g for g in r["byAssetGroupType"] if g["networkSource"] == "ElectricDevice"][0]
        self.assertEqual((dev["assetGroup"], dev["assetType"]), ("Breaker", "Recloser"))
        path, q = [c for c in self.srv.calls if c[0].endswith("/trace")][-1]
        self.assertEqual(q["gdbVersion"], "crew1.outage")
        self.assertNotIn("sessionId", q)  # read-only trace: no session
        locs = json.loads(q["traceLocations"])
        self.assertEqual(locs[0], {"traceLocationType": "startingPoint",
                                   "globalId": "{8F2A6C1E-4B7D-4E1A-9C55-2D0F7A1B3E90}", "terminalId": 2})

    def test_trace_rejects_a_start_without_terminal_or_percent(self):
        with self.assertRaises(Exception) as cm:
            call(self.server(), "trace", {"trace_type": "downstream",
                                          "starting_points": [{"globalId": "{A}"}]})
        self.assertIn("terminalId", str(cm.exception))

    # -- auth ----------------------------------------------------------------
    def test_oauth_client_credentials_flow(self):
        os.environ.pop("UN_TOKEN")
        os.environ["UN_PORTAL_URL"] = f"{self.base}/portal"
        os.environ["UN_CLIENT_ID"], os.environ["UN_CLIENT_SECRET"] = "cid", "sec"
        r = call(self.server(), "describe_network")
        self.assertEqual(r["utilityNetworkLayerId"], 9)
        self.assertTrue(any(p.endswith("/oauth2/token") for p, _ in self.srv.calls))

    def test_bad_token_surfaces_the_service_error(self):
        os.environ["UN_TOKEN"] = "WRONG"
        with self.assertRaises(Exception) as cm:
            call(self.server(), "describe_network")
        self.assertIn("Invalid token", str(cm.exception))

    def test_job_status_only_polls_the_configured_server(self):
        with self.assertRaises(Exception):
            call(self.server(), "job_status", {"status_url": "https://evil.example/rest/jobs/1"})


if __name__ == "__main__":
    unittest.main()
