"""Shared cleaning helpers used across datasets."""

from __future__ import annotations

import pandas as pd


def trim_whitespace(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    cleaned = frame.copy()
    for column in columns:
        if column in cleaned.columns:
            cleaned[column] = cleaned[column].map(lambda value: str(value).strip())
    return cleaned


def lowercase_text(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    cleaned = frame.copy()
    for column in columns:
        if column in cleaned.columns:
            cleaned[column] = cleaned[column].map(lambda value: str(value).strip().lower())
    return cleaned


def replace_empty_cells(frame: pd.DataFrame, columns: list[str], replacement: str) -> pd.DataFrame:
    cleaned = frame.copy()
    for column in columns:
        if column in cleaned.columns:
            cleaned[column] = cleaned[column].map(
                lambda value: replacement if str(value).strip() == "" else str(value).strip()
            )
    return cleaned


def drop_fully_empty_rows(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    if frame.empty:
        return frame

    data_columns = [column for column in columns if column in frame.columns]
    if not data_columns:
        return frame

    non_empty_mask = frame[data_columns].apply(
        lambda row: any(str(value).strip() for value in row),
        axis=1,
    )
    return frame.loc[non_empty_mask].copy()


def drop_fully_duplicated_rows(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    data_columns = [column for column in columns if column in frame.columns]
    if not data_columns:
        return frame

    return frame.drop_duplicates(subset=data_columns, keep="first").reset_index(drop=True)
