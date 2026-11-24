"""Statische Sicherheitsregression für die Modell-Spikes."""
import ast
from pathlib import Path
import unittest

SPIKES = Path(__file__).resolve().parents[2] / "benchmarks" / "spikes"


class SpikeWeightSafetyTests(unittest.TestCase):
    def test_no_explicit_unsafe_weight_load(self):
        scripts = sorted(SPIKES.glob("*/messen.py"))
        self.assertTrue(scripts)
        for path in scripts:
            with self.subTest(path=path.name, candidate=path.parent.name):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        self.assertFalse(
                            isinstance(node.func, ast.Attribute)
                            and isinstance(node.func.value, ast.Name)
                            and node.func.value.id == "pickle"
                            and node.func.attr in ("load", "loads")
                        )
                        for keyword in node.keywords:
                            if keyword.arg == "weights_only":
                                self.assertNotEqual(
                                    getattr(keyword.value, "value", None), False
                                )
