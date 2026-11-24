"""Tests für die Echtzeit-Schicht."""
import os

# Tests laufen unabhängig davon, welche Modell-Umgebungen auf dem Rechner installiert sind.
os.environ.setdefault("SIRENS_RT_AUTODETECT", "aus")
