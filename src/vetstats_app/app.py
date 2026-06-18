import sys

from PyQt6.QtWidgets import QApplication

from vetstats_app.services.app_event_logger import start_new_session
from vetstats_app.ui.main_window import MainWindow


def run() -> int:
    start_new_session()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
