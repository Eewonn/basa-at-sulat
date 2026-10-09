import sys
from pathlib import Path

# The guard lives in scripts/ so the engine and scripts suites share one implementation.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import netguard  # noqa: E402


def pytest_configure(config):
    netguard.install()
