from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


def text_section(title: str, text: str) -> QGroupBox:
    group = QGroupBox(title)
    layout = QVBoxLayout(group)
    layout.addWidget(QLabel(text))
    return group


class AutomaticModulePage(QWidget):
    def __init__(
        self,
        module_title: str,
        section_groups: list[QGroupBox],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        title_label = QLabel(module_title)

        generate_report_button = QPushButton("Generuj raport")
        export_charts_button = QPushButton("Eksport wykresów")

        action_bar = QHBoxLayout()
        action_bar.addWidget(generate_report_button)
        action_bar.addWidget(export_charts_button)
        action_bar.addStretch()

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        for section in section_groups:
            content_layout.addWidget(section)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(content_widget)

        layout = QVBoxLayout(self)
        layout.addWidget(title_label)
        layout.addLayout(action_bar)
        layout.addWidget(scroll_area, stretch=1)
