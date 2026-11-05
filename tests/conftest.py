import os
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

@pytest.fixture(scope="session", autouse=True)
def qapp():
    """Ensure a single global QApplication lives for the entire test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(["synctree-test"])
    yield app
