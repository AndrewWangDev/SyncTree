import os
import sys
import gc
import pytest

# Ensure offscreen Qt platform before any QApplication or widget is instantiated
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

@pytest.fixture(scope="session", autouse=True)
def qapp():
    """Ensure a single global QApplication lives for the entire test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(["synctree-test"])
    yield app
    for widget in app.topLevelWidgets():
        try:
            if hasattr(widget, "poller") and widget.poller and widget.poller.isRunning():
                widget.poller.stop()
                widget.poller.wait(500)
            widget.close()
            widget.deleteLater()
        except Exception:
            pass
    app.processEvents()

@pytest.fixture(autouse=True)
def cleanup_qt_widgets():
    """Clean up any widgets created during individual tests to prevent dangling C++ objects."""
    yield
    app = QApplication.instance()
    if app:
        for widget in app.topLevelWidgets():
            try:
                if hasattr(widget, "poller") and widget.poller and widget.poller.isRunning():
                    widget.poller.stop()
                    widget.poller.wait(200)
                widget.close()
                widget.deleteLater()
            except Exception:
                pass
        app.processEvents()
    gc.collect()

def pytest_sessionfinish(session, exitstatus):
    app = QApplication.instance()
    if app:
        for widget in app.topLevelWidgets():
            try:
                if hasattr(widget, "poller") and widget.poller and widget.poller.isRunning():
                    widget.poller.stop()
                    widget.poller.wait(200)
                widget.close()
                widget.deleteLater()
            except Exception:
                pass
        app.closeAllWindows()
        app.processEvents()
