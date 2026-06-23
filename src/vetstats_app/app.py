import sys

from PyQt6.QtWidgets import QApplication

from vetstats_app.services.app_event_logger import start_new_session
from vetstats_app.services.branding import load_window_icon
from vetstats_app.ui.main_window import MainWindow


def run() -> int:
    start_new_session()
    app = QApplication(sys.argv)
    window_icon = load_window_icon()
    if window_icon is not None:
        app.setWindowIcon(window_icon)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
