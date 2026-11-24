import contextlib
import io
import unittest
from unittest.mock import patch

from benchmarks.neural_mutation import messen


class NeuralMutationBenchmark(unittest.TestCase):
    def test_dry_run(self):
        with patch.object(messen, "measure", side_effect=AssertionError("Keine Inferenz")):
            for name in ("rave", "after"):
                with contextlib.redirect_stdout(io.StringIO()) as out:
                    self.assertEqual(messen.main([name, "--dry-run"]), 0)
                self.assertIn("nicht_gemessen", out.getvalue())
                self.assertEqual(len(messen.cases(name)), 3)
