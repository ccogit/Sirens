"""Vertragsgrenzen für den Mock-Durchstich (ohne GPU)."""
import unittest

from sirens.contracts import Ablehnung
from sirens.realtime.contracts import (
    SESSION_TRANSITIONS, transition, validate_command, source_path,
)
from tempfile import TemporaryDirectory
from pathlib import Path


class MockE2EContractTests(unittest.TestCase):
    def test_session_transitions(self):
        state = "created"
        for target in ("loading", "ready", "playing", "paused", "playing",
                       "stopping", "closed"):
            state = transition(SESSION_TRANSITIONS, state, target)
        with self.assertRaises(Ablehnung):
            transition(SESSION_TRANSITIONS, state, "playing")

    def test_old_epoch_rejected(self):
        with self.assertRaises(Ablehnung):
            validate_command({"command": "play", "epoch": 0, "seq": 0,
                              "args": {}}, 1)

    def test_source_traversal_rejected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory) / "music"
            root.mkdir()
            (root.parent / "outside.wav").touch()
            with self.assertRaises(Ablehnung):
                source_path(root, "../outside.wav")
