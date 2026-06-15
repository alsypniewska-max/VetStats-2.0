from PyQt6.QtWidgets import QHBoxLayout, QStackedWidget, QVBoxLayout, QWidget

from vetstats_app.ui.analysis.automatic_section import AutomaticAnalysisSection
from vetstats_app.ui.analysis.detailed_section import DetailedAnalysisSection
from vetstats_app.ui.analysis.section_nav_panel import SectionNavPanel


class AnalysisPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        section_nav_panel = SectionNavPanel()

        section_stack = QStackedWidget()
        section_stack.addWidget(AutomaticAnalysisSection())
        section_stack.addWidget(DetailedAnalysisSection())

        body = QHBoxLayout()
        body.addWidget(section_nav_panel)
        body.addWidget(section_stack, stretch=1)

        layout = QVBoxLayout(self)
        layout.addLayout(body)

        section_nav_panel.connect_current_row_changed(section_stack.setCurrentIndex)
        section_nav_panel.set_current_row(0)
