from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from vetstats_app.analysis.detailed_comparative import (
    MAX_CRITERIA_PER_GROUP,
    ComparativeGroupDefinition,
    GroupCriterion,
)
from vetstats_app.ui.analysis.analysis_button_style import apply_compact_analysis_button_style
from vetstats_app.ui.analysis.detailed_criterion_widget import DetailedCriterionWidget


class DetailedGroupWidget(QWidget):
    def __init__(
        self,
        *,
        title: str,
        default_name: str,
        locked_structure: bool,
        list_tables: Callable[[], tuple[str, ...]],
        list_columns: Callable[[str], tuple[str, ...]],
        list_values: Callable[[str, str], tuple[str, ...]],
        on_changed: Callable[[], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._default_name = default_name
        self._locked_structure = locked_structure
        self._list_tables = list_tables
        self._list_columns = list_columns
        self._list_values = list_values
        self._on_changed = on_changed
        self._criterion_widgets: list[DetailedCriterionWidget] = []

        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText(default_name)

        add_button = QPushButton("Dodaj kryterium")
        apply_compact_analysis_button_style(add_button)
        add_button.clicked.connect(self._add_criterion)

        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Nazwa grupy:"))
        name_layout.addWidget(self._name_input, stretch=1)
        if not locked_structure:
            name_layout.addWidget(add_button)

        self._criteria_layout = QVBoxLayout()
        self._criteria_layout.setContentsMargins(0, 0, 0, 0)
        self._criteria_layout.setSpacing(8)

        self._empty_label = QLabel("Brak kryteriów.")
        self._criteria_layout.addWidget(self._empty_label)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(title))
        layout.addLayout(name_layout)
        layout.addLayout(self._criteria_layout)

        self._name_input.textChanged.connect(lambda _text: self._on_changed())

    def set_group(self, group: ComparativeGroupDefinition) -> None:
        self._name_input.blockSignals(True)
        self._name_input.setText(group.custom_name)
        if not group.custom_name:
            self._name_input.clear()
        self._name_input.blockSignals(False)

        while self._criterion_widgets:
            self._remove_criterion_widget(0, emit=False)

        for criterion in group.criteria:
            self._add_criterion_widget(criterion, emit=False)

        self._update_empty_state()

    def get_group(self) -> ComparativeGroupDefinition:
        return ComparativeGroupDefinition(
            default_name=self._default_name,
            custom_name=self._name_input.text().strip(),
            criteria=tuple(widget.get_criterion() for widget in self._criterion_widgets),
        )

    def refresh_dynamic_options(self) -> None:
        for widget in self._criterion_widgets:
            widget.refresh_dynamic_options()

    def _add_criterion(self) -> None:
        if len(self._criterion_widgets) >= MAX_CRITERIA_PER_GROUP:
            return
        self._add_criterion_widget(GroupCriterion("", "", ""))

    def _add_criterion_widget(
        self,
        criterion: GroupCriterion,
        *,
        emit: bool = True,
    ) -> None:
        if len(self._criterion_widgets) >= MAX_CRITERIA_PER_GROUP:
            return

        widget = DetailedCriterionWidget(
            locked_structure=self._locked_structure,
            list_tables=self._list_tables,
            list_columns=self._list_columns,
            list_values=self._list_values,
            on_changed=self._on_changed,
            on_remove=lambda: self._remove_widget(widget),
        )
        widget.set_criterion(criterion)
        self._criterion_widgets.append(widget)
        self._criteria_layout.addWidget(widget)
        self._update_empty_state()
        if emit:
            self._on_changed()

    def _remove_widget(self, widget: DetailedCriterionWidget) -> None:
        try:
            index = self._criterion_widgets.index(widget)
        except ValueError:
            return
        self._remove_criterion_widget(index)

    def _remove_criterion_widget(self, index: int, *, emit: bool = True) -> None:
        if index < 0 or index >= len(self._criterion_widgets):
            return
        widget = self._criterion_widgets.pop(index)
        self._criteria_layout.removeWidget(widget)
        widget.deleteLater()
        self._update_empty_state()
        if emit:
            self._on_changed()

    def _update_empty_state(self) -> None:
        self._empty_label.setVisible(len(self._criterion_widgets) == 0)
