from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from vetstats_app.analysis.detailed_comparative import (
    CriterionMode,
    CriterionModeLabel,
    GroupCriterion,
)
from vetstats_app.ui.analysis.analysis_button_style import apply_compact_analysis_button_style


class DetailedCriterionWidget(QWidget):
  def __init__(
      self,
      *,
      locked_structure: bool,
      list_tables: Callable[[], tuple[str, ...]],
      list_columns: Callable[[str], tuple[str, ...]],
      list_values: Callable[[str, str], tuple[str, ...]],
      on_changed: Callable[[], None],
      on_remove: Callable[[], None],
      parent: QWidget | None = None,
  ) -> None:
      super().__init__(parent)
      self._locked_structure = locked_structure
      self._list_tables = list_tables
      self._list_columns = list_columns
      self._list_values = list_values
      self._on_changed = on_changed
      self._suppress_events = False

      self._table_combo = QComboBox()
      self._column_combo = QComboBox()
      self._value_combo = QComboBox()
      self._table_label = QLabel()
      self._column_label = QLabel()

      self._may_radio = QRadioButton(CriterionModeLabel.MAY)
      self._must_radio = QRadioButton(CriterionModeLabel.MUST)
      self._must_radio.setChecked(True)
      self._mode_group = QButtonGroup(self)
      self._mode_group.addButton(self._may_radio, 0)
      self._mode_group.addButton(self._must_radio, 1)

      remove_button = QPushButton("Usuń")
      apply_compact_analysis_button_style(remove_button)
      remove_button.clicked.connect(on_remove)
      if locked_structure:
          remove_button.setVisible(False)

      mode_layout = QHBoxLayout()
      mode_layout.setContentsMargins(0, 0, 0, 0)
      mode_layout.addWidget(QLabel("Tryb:"))
      mode_layout.addWidget(self._may_radio)
      mode_layout.addWidget(self._must_radio)
      mode_layout.addStretch()

      row_layout = QHBoxLayout()
      row_layout.setContentsMargins(0, 0, 0, 0)
      row_layout.addWidget(QLabel("Tabela:"))
      if locked_structure:
          row_layout.addWidget(self._table_label)
          row_layout.addWidget(QLabel("Kolumna:"))
          row_layout.addWidget(self._column_label)
      else:
          row_layout.addWidget(self._table_combo)
          row_layout.addWidget(QLabel("Kolumna:"))
          row_layout.addWidget(self._column_combo)
      row_layout.addWidget(QLabel("Wartość:"))
      row_layout.addWidget(self._value_combo, stretch=1)
      row_layout.addWidget(remove_button)

      layout = QVBoxLayout(self)
      layout.setContentsMargins(0, 0, 0, 0)
      layout.addLayout(row_layout)
      layout.addLayout(mode_layout)

      if not locked_structure:
          self._table_combo.currentTextChanged.connect(self._on_table_changed)
          self._column_combo.currentTextChanged.connect(self._on_column_changed)
      self._value_combo.currentTextChanged.connect(self._emit_changed)
      self._mode_group.idClicked.connect(lambda _id: self._emit_changed())

      if locked_structure:
          self._may_radio.setEnabled(False)
          self._must_radio.setEnabled(False)

      self._refresh_table_options()

  def set_criterion(self, criterion: GroupCriterion) -> None:
      self._suppress_events = True
      try:
          if self._locked_structure:
              self._table_label.setText(criterion.table_name or "—")
              self._column_label.setText(criterion.column_name or "—")
              self._reload_values(criterion.table_name, criterion.column_name, criterion.value)
          else:
              self._set_combo_value(self._table_combo, criterion.table_name)
              self._reload_columns(criterion.table_name, criterion.column_name)
              self._reload_values(criterion.table_name, criterion.column_name, criterion.value)

          if criterion.mode == CriterionMode.MAY_CONTAIN:
              self._may_radio.setChecked(True)
          else:
              self._must_radio.setChecked(True)
      finally:
          self._suppress_events = False

  def get_criterion(self) -> GroupCriterion:
      if self._locked_structure:
          table_name = self._table_label.text().strip()
          column_name = self._column_label.text().strip()
          if table_name == "—":
              table_name = ""
          if column_name == "—":
              column_name = ""
      else:
          table_name = self._table_combo.currentText().strip()
          column_name = self._column_combo.currentText().strip()

      mode = (
          CriterionMode.MAY_CONTAIN
          if self._may_radio.isChecked()
          else CriterionMode.MUST_CONTAIN
      )
      return GroupCriterion(
          table_name=table_name,
          column_name=column_name,
          value=self._value_combo.currentText().strip(),
          mode=mode,
      )

  def _emit_changed(self) -> None:
      if self._suppress_events:
          return
      self._on_changed()

  def _on_table_changed(self, table_name: str) -> None:
      if self._suppress_events:
          return
      self._reload_columns(table_name, "")
      self._reload_values(table_name, "", "")
      self._emit_changed()

  def _on_column_changed(self, column_name: str) -> None:
      if self._suppress_events:
          return
      table_name = self._table_combo.currentText().strip()
      self._reload_values(table_name, column_name, "")
      self._emit_changed()

  def _refresh_table_options(self) -> None:
      if self._locked_structure:
          return
      current = self._table_combo.currentText()
      self._table_combo.blockSignals(True)
      self._table_combo.clear()
      self._table_combo.addItems(list(self._list_tables()))
      if current:
          self._set_combo_value(self._table_combo, current)
      self._table_combo.blockSignals(False)

  def refresh_dynamic_options(self) -> None:
      criterion = self.get_criterion()
      self._refresh_table_options()
      self.set_criterion(criterion)

  def _reload_columns(self, table_name: str, selected_column: str) -> None:
      self._column_combo.blockSignals(True)
      self._column_combo.clear()
      if table_name:
          self._column_combo.addItems(list(self._list_columns(table_name)))
      if selected_column:
          self._set_combo_value(self._column_combo, selected_column)
      self._column_combo.blockSignals(False)

  def _reload_values(self, table_name: str, column_name: str, selected_value: str) -> None:
      self._value_combo.blockSignals(True)
      self._value_combo.clear()
      if table_name and column_name:
          self._value_combo.addItems(
              list(self._list_values(table_name, column_name))
          )
      if selected_value:
          if self._value_combo.findText(selected_value) < 0:
              self._value_combo.addItem(selected_value)
          self._set_combo_value(self._value_combo, selected_value)
      self._value_combo.blockSignals(False)

  @staticmethod
  def _set_combo_value(combo: QComboBox, value: str) -> None:
      index = combo.findText(value)
      if index >= 0:
          combo.setCurrentIndex(index)
      elif value:
          combo.addItem(value)
          combo.setCurrentIndex(combo.count() - 1)
      else:
          combo.setCurrentIndex(-1)
