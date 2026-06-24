from PyQt6.QtWidgets import QHBoxLayout, QStackedWidget, QVBoxLayout, QWidget

from vetstats_app.ui.analysis.automatic_module_nav_panel import AutomaticModuleNavPanel
from vetstats_app.ui.analysis.automatic_section import AutomaticAnalysisSection
from vetstats_app.ui.analysis.detailed_section import DetailedAnalysisSection
from vetstats_app.ui.analysis.section_switch_bar import SectionSwitchBar


class AnalysisPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        section_switch_bar = SectionSwitchBar()
        module_nav_panel = AutomaticModuleNavPanel()

        automatic_section = AutomaticAnalysisSection()
        detailed_section = DetailedAnalysisSection()
        self._detailed_section = detailed_section

        content_stack = QStackedWidget()
        content_stack.addWidget(automatic_section)
        content_stack.addWidget(detailed_section)

        content_column = QVBoxLayout()
        content_column.setContentsMargins(0, 0, 0, 0)
        content_column.addWidget(section_switch_bar)
        content_column.addWidget(automatic_section.action_bar_stack)
        content_column.addWidget(content_stack, stretch=1)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.addWidget(module_nav_panel)
        body.addLayout(content_column, stretch=1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(body, stretch=1)

        section_switch_bar.connect_section_changed(self._on_section_changed)
        module_nav_panel.connect_current_row_changed(automatic_section.set_current_module)

        self._module_nav_panel = module_nav_panel
        self._content_stack = content_stack
        self._action_bar_stack = automatic_section.action_bar_stack

        section_switch_bar.set_current_section(0)
        self._on_section_changed(0)

    def detailed_analysis_context(self):
        from vetstats_app.services.full_report_service import DetailedAnalysisContext

        return DetailedAnalysisContext(
            state=self._detailed_section.collect_state_for_full_report(),
            last_result=self._detailed_section.last_result(),
        )

    def _on_section_changed(self, index: int) -> None:
        self._content_stack.setCurrentIndex(index)
        self._module_nav_panel.setVisible(index == 0)
        self._action_bar_stack.setVisible(index == 0)
