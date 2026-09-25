from pathlib import Path
from typing import Any
import uuid

import great_expectations as gx
import great_expectations.expectations as gxe
import pandas as pd

from core.config import Settings
from core.utils import safe_slug, write_json


def build_freshness_report(
    df: pd.DataFrame,
    settings: Settings,
    report_path: Path | str | None = None,
) -> dict[str, Any]:
    """Calculate dataset freshness metrics and write report if requested."""
    total_rows = len(df)
    if total_rows == 0:
        report = {
            "total_rows": 0,
            "latest_published": "N/A",
            "oldest_published": "N/A",
            "stale_rows": 0,
            "stale_ratio": 0.0,
            "freshness_threshold_days": settings.freshness_threshold_days,
            "is_fresh": False,
        }
    else:
        latest_published = str(df["published"].max()) if "published" in df.columns else "N/A"
        oldest_published = str(df["published"].min()) if "published" in df.columns else "N/A"
        threshold = settings.freshness_threshold_days

        if "age_days" in df.columns:
            stale_rows = int((df["age_days"] > threshold).sum())
        else:
            stale_rows = 0

        stale_ratio = stale_rows / total_rows if total_rows > 0 else 0.0
        # Fresh if stale records ratio is <= 25%
        is_fresh = bool(stale_ratio <= 0.25)

        report = {
            "total_rows": total_rows,
            "latest_published": latest_published,
            "oldest_published": oldest_published,
            "stale_rows": stale_rows,
            "stale_ratio": round(stale_ratio, 4),
            "freshness_threshold_days": threshold,
            "is_fresh": is_fresh,
        }

    if report_path:
        write_json(Path(report_path), report)

    return report


def run_data_quality_checks(
    df: pd.DataFrame,
    settings: Settings,
    report_name: str,
) -> dict[str, Any]:
    """Execute Great Expectations 1.x validation suite and Freshness SLA checks."""
    safe_name = safe_slug(report_name)
    run_id = uuid.uuid4().hex[:6]

    # Initialize Great Expectations 1.x ephemeral context
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name=f"papers_source_{safe_name}_{run_id}")
    data_asset = data_source.add_dataframe_asset(name=f"papers_asset_{safe_name}_{run_id}")
    batch_def = data_asset.add_batch_definition_whole_dataframe(f"papers_batch_{safe_name}_{run_id}")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    # Define GX 1.x Expectation Suite
    suite = gx.ExpectationSuite(name=f"papers_suite_{safe_name}_{run_id}")
    suite.add_expectation(gxe.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000))

    if "paper_id" in df.columns:
        suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="paper_id"))
        suite.add_expectation(gxe.ExpectColumnValuesToBeUnique(column="paper_id"))
    else:
        suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="paper_id"))

    if "title" in df.columns:
        suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="title"))

    if "text_for_embedding" in df.columns:
        suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="text_for_embedding"))

    if "summary" in df.columns:
        suite.add_expectation(gxe.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30))

    validation_result = batch.validate(suite)
    gx_success = bool(validation_result.success)

    # Freshness Check
    freshness_report_path = (
        settings.paths.freshness_report if report_name in {"baseline", "test"} else None
    )
    freshness = build_freshness_report(df, settings, freshness_report_path)

    overall_success = bool(gx_success and freshness["is_fresh"])

    # Extract expectation results
    expectation_results = []
    for r in getattr(validation_result, "results", []):
        exp_type = getattr(r.expectation_config, "type", "unknown")
        expectation_results.append(
            {
                "expectation": exp_type,
                "success": bool(r.success),
            }
        )

    report_payload = {
        "report_name": report_name,
        "success": overall_success,
        "gx_success": gx_success,
        "is_fresh": freshness["is_fresh"],
        "total_rows": len(df),
        "freshness": freshness,
        "expectations": expectation_results,
    }

    # Determine report destination path
    if report_name == "baseline":
        dest_path = settings.paths.baseline_quality_report
    elif report_name == "corrupted":
        dest_path = settings.paths.corrupted_quality_report
    else:
        dest_path = settings.paths.quality_dir / f"{safe_name}_quality_report.json"

    write_json(dest_path, report_payload)
    return report_payload
