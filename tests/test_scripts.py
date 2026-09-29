"""Tests for the helper scripts: dirty-area decoder and trace request validator."""
import importlib.util
import json
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "plugins/utility-network/skills/utility-network/scripts"
EXAMPLES = ROOT / "examples/isolation-trace"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


decode_mod = load("decode_dirty_status")
trace_mod = load("build_trace_request")


class DirtyStatus(unittest.TestCase):
    def test_edit_only_values_are_cleared_by_validate(self):
        for s in (1, 2, 4, 3, 7):
            d = decode_mod.decode(s)
            self.assertEqual(d["kind"], "edit only", s)
            self.assertTrue(d["validate_evaluates"], s)

    def test_error_only_values_are_ignored_by_validate(self):
        for s in (8, 16, 32, 24, 40, 48, 56):
            d = decode_mod.decode(s)
            self.assertEqual(d["kind"], "error only", s)
            self.assertFalse(d["validate_evaluates"], s)
            self.assertIn("EDITING", d["action"], s)

    def test_edit_plus_error(self):
        for s in (9, 17, 33, 41):
            d = decode_mod.decode(s)
            self.assertEqual(d["kind"], "edit + error", s)
            self.assertTrue(d["validate_evaluates"], s)

    def test_specific_decodes_from_the_readme(self):
        self.assertEqual(decode_mod.decode(9)["meanings"], ["feature inserted or updated", "feature error"])
        self.assertEqual(decode_mod.decode(40)["meanings"], ["feature error", "subnetwork error"])
        self.assertIn("Update Subnetwork", decode_mod.decode(40)["action"])

    def test_zero_means_topology_disabled(self):
        self.assertEqual(decode_mod.decode(0)["kind"], "disabled")

    def test_out_of_range_is_a_clean_error_not_a_traceback(self):
        r = subprocess.run([sys.executable, str(SCRIPTS / "decode_dirty_status.py"), "64"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertNotIn("Traceback", r.stderr)
        with self.assertRaises(ValueError):
            decode_mod.decode(-1)


class TraceValidator(unittest.TestCase):
    def analyze(self, name):
        return trace_mod.analyze(json.loads((EXAMPLES / name).read_text()))

    def test_good_isolation_request_is_clean(self):
        problems, warnings = self.analyze("request.json")
        self.assertEqual(problems, [])
        self.assertEqual(warnings, [])

    def test_broken_request_reports_every_planted_mistake(self):
        problems, _ = self.analyze("request.broken.json")
        text = "\n".join(problems)
        for needle in ("sessionId", "percentAlong must be 0-1", "needs terminalId",
                       "unknown key 'tierNam'", "name is required", "operator 'equals'"):
            self.assertIn(needle, text)

    def test_numeric_condition_value_is_only_a_warning(self):
        req = json.loads((EXAMPLES / "request.json").read_text())
        req["traceConfiguration"]["filterBarriers"][1]["value"] = 1
        problems, warnings = trace_mod.analyze(req)
        self.assertEqual(problems, [])
        self.assertTrue(any("is a number" in w for w in warnings))

    def test_session_id_alone_triggers_the_read_only_hint(self):
        req = json.loads((EXAMPLES / "request.json").read_text())
        req["sessionId"] = "{3F2504E0-4F89-41D3-9A0C-0305E82C3301}"
        problems, warnings = trace_mod.analyze(req)
        self.assertEqual(problems, [])
        self.assertTrue(any("only needed when THIS client holds" in w for w in warnings))

    def test_edge_start_without_percent_along_is_a_problem(self):
        req = json.loads((EXAMPLES / "request.json").read_text())
        del req["traceLocations"][0]["percentAlong"]
        problems, _ = trace_mod.analyze(req)
        self.assertTrue(any("silently ignores" in p for p in problems))

    def test_cli_exit_codes(self):
        run = lambda f: subprocess.run([sys.executable, str(SCRIPTS / "build_trace_request.py"),
                                        "--check", str(EXAMPLES / f)], capture_output=True, text=True)
        self.assertEqual(run("request.json").returncode, 0)
        self.assertEqual(run("request.broken.json").returncode, 1)


if __name__ == "__main__":
    unittest.main()
