"""Validation issue tracking (minimal scaffold for the pipeline)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class Issue:
    severity: Severity
    dataset: str
    row: int | None
    column: str | None
    message: str


@dataclass
class ValidationReport:
    issues: list[Issue] = field(default_factory=list)

    def add(self, issue: Issue) -> None:
        self.issues.append(issue)

    def extend(self, other: ValidationReport) -> None:
        self.issues.extend(other.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity is Severity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity is Severity.WARNING)

    def has_errors(self) -> bool:
        return self.error_count > 0

    @property
    def cross_file_issues(self) -> list[Issue]:
        return [issue for issue in self.issues if issue.dataset == "cross_file"]

    @property
    def table_issues(self) -> list[Issue]:
        return [issue for issue in self.issues if issue.dataset != "cross_file"]
