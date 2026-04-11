from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.utils.dates import excel_serial_to_date
from src.utils.numbers import coerce_numeric


class DataQualityError(ValueError):
    """Raised when a pipeline quality gate fails."""


@dataclass(frozen=True)
class QualityCheckResult:
    stage: str
    dataset: str
    issue: str
    details: str

    def format_message(self, domain: str) -> str:
        return f"[{domain}:{self.stage}] {self.dataset}: {self.issue} ({self.details})"


def _non_empty_mask(series: pd.Series) -> pd.Series:
    as_text = series.astype("string")
    return series.notna() & as_text.str.strip().ne("")


def _sample_rows(frame: pd.DataFrame, mask: pd.Series, column: str, limit: int = 5) -> str:
    if frame.empty or not mask.any():
        return "no samples"
    samples = []
    for row_no, value in frame.loc[mask, column].head(limit).items():
        samples.append(f"row={int(row_no) + 2}, value={value!r}")
    return "; ".join(samples)


def _parse_dates(series: pd.Series) -> pd.Series:
    return series.map(excel_serial_to_date)


def _parse_numbers(series: pd.Series) -> pd.Series:
    return series.map(coerce_numeric)


def _raise_if_any(domain: str, results: list[QualityCheckResult]) -> None:
    if not results:
        return
    message = "\n".join(result.format_message(domain) for result in results)
    raise DataQualityError(message)


def run_pre_checks(
    frame: pd.DataFrame,
    *,
    domain: str,
    dataset: str,
    required_columns: list[str],
    date_columns: list[str],
    amount_columns: list[str],
) -> None:
    results: list[QualityCheckResult] = []

    missing_columns = [column for column in required_columns if column not in frame.columns]
    if missing_columns:
        results.append(
            QualityCheckResult(
                stage="pre-check",
                dataset=dataset,
                issue="missing required columns",
                details=", ".join(missing_columns),
            )
        )
        _raise_if_any(domain, results)

    for column in date_columns:
        if column not in frame.columns:
            continue
        parsed = _parse_dates(frame[column])
        invalid_mask = _non_empty_mask(frame[column]) & parsed.isna()
        if invalid_mask.any():
            results.append(
                QualityCheckResult(
                    stage="pre-check",
                    dataset=dataset,
                    issue=f"unparseable date column `{column}`",
                    details=_sample_rows(frame, invalid_mask, column),
                )
            )

    for column in amount_columns:
        if column not in frame.columns:
            continue
        parsed = _parse_numbers(frame[column])
        populated_mask = _non_empty_mask(frame[column])
        invalid_mask = populated_mask & parsed.isna()
        negative_mask = parsed.fillna(0) < 0
        if invalid_mask.any():
            results.append(
                QualityCheckResult(
                    stage="pre-check",
                    dataset=dataset,
                    issue=f"non-numeric amount column `{column}`",
                    details=_sample_rows(frame, invalid_mask, column),
                )
            )
        if negative_mask.any():
            results.append(
                QualityCheckResult(
                    stage="pre-check",
                    dataset=dataset,
                    issue=f"negative amount column `{column}`",
                    details=_sample_rows(frame, negative_mask, column),
                )
            )

    _raise_if_any(domain, results)


def _detect_iqr_outliers(series: pd.Series) -> pd.Series:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty or len(clean) < 4:
        return pd.Series(False, index=series.index)
    q1 = clean.quantile(0.25)
    q3 = clean.quantile(0.75)
    iqr = q3 - q1
    if pd.isna(iqr) or iqr == 0:
        return pd.Series(False, index=series.index)
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    return (pd.to_numeric(series, errors="coerce") < lower) | (pd.to_numeric(series, errors="coerce") > upper)


def _detect_zscore_outliers(series: pd.Series, threshold: float) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    clean = numeric.dropna()
    if clean.empty or len(clean) < 3:
        return pd.Series(False, index=series.index)
    std = clean.std(ddof=0)
    if pd.isna(std) or std == 0:
        return pd.Series(False, index=series.index)
    mean = clean.mean()
    zscores = ((numeric - mean) / std).abs()
    return zscores > threshold


def run_post_checks(
    frame: pd.DataFrame,
    *,
    domain: str,
    dataset: str,
    amount_columns: list[str],
    date_ranges: list[tuple[str, str]],
    zscore_threshold: float = 3.0,
) -> None:
    if frame.empty:
        return

    results: list[QualityCheckResult] = []

    for column in amount_columns:
        if column not in frame.columns:
            continue
        numeric = pd.to_numeric(frame[column], errors="coerce")
        outlier_mask = _detect_iqr_outliers(numeric) | _detect_zscore_outliers(numeric, threshold=zscore_threshold)
        if outlier_mask.any():
            results.append(
                QualityCheckResult(
                    stage="post-check",
                    dataset=dataset,
                    issue=f"amount anomaly in `{column}`",
                    details=_sample_rows(frame, outlier_mask.fillna(False), column),
                )
            )

    for start_column, end_column in date_ranges:
        if start_column not in frame.columns or end_column not in frame.columns:
            continue
        start_dates = pd.to_datetime(frame[start_column], errors="coerce")
        end_dates = pd.to_datetime(frame[end_column], errors="coerce")
        invalid_mask = start_dates.notna() & end_dates.notna() & (end_dates < start_dates)
        if invalid_mask.any():
            results.append(
                QualityCheckResult(
                    stage="post-check",
                    dataset=dataset,
                    issue=f"invalid date range `{end_column} < {start_column}`",
                    details=_sample_rows(frame, invalid_mask, end_column),
                )
            )

    _raise_if_any(domain, results)
