"""Netz- und GPU-freie Regressionen für AUFGABE-23."""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from benchmarks.spikes.rave import install as rave
from benchmarks.spikes.after import install as after
from benchmarks.spikes.after.messen import transfer


class RaveAfterTests(unittest.TestCase):
    def test_manifest_fields(self):
        item = rave.manifest()
        self.assertEqual(item["size_bytes"], 163881670)
        self.assertEqual(len(item["sha256"]), 64)
        self.assertEqual((item["rate"], item["block"]), (48000, 2048))
        other = json.loads((after.HERE / "weights.json").read_text(encoding="utf-8"))["models"][0]
        self.assertTrue({"filename", "size_bytes", "sha256", "license", "url"} <= other.keys())
        self.assertFalse(other["approved"])

    def test_no_network_without_switch(self):
        with patch.object(rave.urllib.request, "urlopen") as net, \
                patch.object(rave.subprocess, "run") as process:
            self.assertEqual(rave.main([]), 0)
            self.assertEqual(after.main([]), 0)
            net.assert_not_called()
            process.assert_not_called()

    def test_rave_rejects_wrong_hash_and_size(self):
        item = dict(approved=True, filename="test.ts", size_bytes=3,
                    sha256=hashlib.sha256(b"abc").hexdigest(), url="https://example.invalid")
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            for bad in (b"bad", b"abcd", b"ab"):
                with patch.object(rave.urllib.request, "urlopen", return_value=io.BytesIO(bad)):
                    with self.assertRaises(ValueError):
                        rave.obtain_weight(item, directory)
                self.assertFalse(list(directory.iterdir()))
            with patch.object(rave.urllib.request, "urlopen", return_value=io.BytesIO(b"abc")) as net:
                target = rave.obtain_weight(item, directory)
                self.assertEqual(target.read_bytes(), b"abc")
                self.assertEqual(rave.obtain_weight(item, directory), target)
                self.assertEqual(net.call_count, 1)

    def test_after_local_export_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.ts"
            source.write_bytes(b"abc")
            directory = root / "weights"
            expected = hashlib.sha256(b"abc").hexdigest()
            with self.assertRaises(ValueError):
                after.register(source, "0" * 64, "Testlizenz", directory)
            with self.assertRaises(ValueError):
                after.register(source, expected, "", directory)
            target = after.register(source, expected, "Testlizenz", directory)
            self.assertEqual(target.read_bytes(), b"abc")
            receipt = json.loads((directory / "local-weight.json").read_text())
            self.assertEqual(receipt["sha256"], expected)
            self.assertEqual(receipt["size_bytes"], 3)

    def test_after_uses_two_sources_and_diffusion(self):
        model = Mock()
        torch = Mock()
        model.emb_model_structure.encode.side_effect = ["structure latent", "timbre latent"]
        model.encoder_time.forward_stream.return_value = "condition"
        model.encoder.forward_stream.return_value = "style"
        model.post_encoder = None
        torch.randn_like.return_value = "noise"
        model.sample.return_value = "new latent"
        model.emb_model_structure.decode.return_value = "audio"
        self.assertEqual(transfer(model, "structure audio", "timbre audio", torch), "audio")
        model.encoder_time.forward_stream.assert_called_once_with("structure latent")
        model.encoder.forward_stream.assert_called_once_with("timbre latent")
        model.sample.assert_called_once_with("noise", time_cond="condition", cond="style")
        model.set_nb_steps.assert_called_once_with(10)
        model.emb_model_structure.decode.assert_called_once_with("new latent")


if __name__ == "__main__":
    unittest.main()
