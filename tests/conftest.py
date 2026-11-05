import os
import pytest

# Fallback to offscreen if neither DISPLAY nor QT_QPA_PLATFORM is provided
if "DISPLAY" not in os.environ and "QT_QPA_PLATFORM" not in os.environ:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

@pytest.fixture(scope="session", autouse=True)
def qapp():
    """Ensure a single global QApplication lives for the entire test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(["synctree-test"])
    yield app
    app.processEvents()

@pytest.fixture(autouse=True)
def process_events_after_test():
    """Process pending Qt events after each test to prevent object buildup."""
    yield
    app = QApplication.instance()
    if app:
        app.processEvents()
