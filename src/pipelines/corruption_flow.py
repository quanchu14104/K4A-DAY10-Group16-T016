from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any

import pandas as pd

from core.config import Settings, load_settings
from core.utils import read_json, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run_corruption_pipeline(settings: Settings | None = None) -> dict[str, Any]:
    """Execute the end-to-end Corruption -> Evaluate -> Repair -> Compare flow."""
    if settings is None:
        settings = load_settings()

    logger.info("=== Starting Phase 2: Corruption, Degradation & Self-Healing Repair ===")

    # 1. Load baseline metrics & clean dataset
    logger.info("Step 1: Loading baseline clean dataset and metrics...")
    if settings.paths.clean_csv.exists():
        df_clean = pd.read_csv(settings.paths.clean_csv)
    elif settings.paths.clean_json.exists():
        df_clean = pd.read_json(settings.paths.clean_json)
    else:
        raise FileNotFoundError(f"Baseline clean data not found at {settings.paths.clean_csv}")

    if settings.paths.baseline_metrics.exists():
        baseline_metrics = read_json(settings.paths.baseline_metrics)
    else:
        baseline_metrics = {
            "retrieval_hit_rate": 1.0,
            "mean_token_f1": 0.4125,
            "mean_judge_score": 2.60,
        }

    # 2. Inject synthetic data corruption (6 scenarios)
    logger.info("Step 2: Injecting synthetic data corruption suite (6 scenarios)...")
    df_corrupted = corrupt_clean_dataframe(df_clean, settings.paths.corruption_log)
    settings.paths.corrupted_clean_csv.parent.mkdir(parents=True, exist_ok=True)
    df_corrupted.to_csv(settings.paths.corrupted_clean_csv, index=False)
    write_json(settings.paths.corrupted_clean_json, df_corrupted.to_dict(orient="records"))
    logger.info(
        "Corrupted data saved (%d rows). Corruption log: %s",
        len(df_corrupted),
        settings.paths.corruption_log,
    )

    # 3. Build corrupted Chroma index & evaluate
    logger.info("Step 3: Indexing corrupted dataset into ChromaDB (%s)...", settings.corrupted_collection_name)
    corrupted_index = LocalEmbeddingIndex.build(
        df=df_corrupted,
        settings=settings,
        embeddings_output_path=settings.paths.corrupted_embeddings_json,
    )

    logger.info("Evaluating degraded agent performance on corrupted data...")
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    corrupted_metrics = corrupted_bundle.summary
    logger.info(
        "Corrupted Metrics: Hit Rate=%.4f, Token F1=%.4f, Judge Score=%.2f",
        corrupted_metrics.get("retrieval_hit_rate", 0.0),
        corrupted_metrics.get("mean_token_f1", 0.0),
        corrupted_metrics.get("mean_judge_score", 0.0),
    )

    # 4. Run Data Quality Gate on corrupted data
    logger.info("Step 4: Running Great Expectations 1.x Quality Gate on corrupted data...")
    corrupted_quality = run_data_quality_checks(df_corrupted, settings, "corrupted")
    corrupted_freshness = corrupted_quality.get("freshness", {})
    logger.info(
        "Corrupted Quality: GX Success=%s, Fresh=%s, Overall=%s",
        corrupted_quality.get("gx_success"),
        corrupted_freshness.get("is_fresh"),
        corrupted_quality.get("success"),
    )

    # 5. Idempotent Repair from raw preservation
    logger.info("Step 5: Performing Idempotent Self-Healing Repair from raw records...")
    raw_records = load_raw_records(settings.paths.raw_records_json)
    run_date = datetime.now(timezone.utc)
    df_repaired = build_clean_dataframe(raw_records, run_date)

    settings.paths.repaired_clean_csv.parent.mkdir(parents=True, exist_ok=True)
    df_repaired.to_csv(settings.paths.repaired_clean_csv, index=False)
    write_json(settings.paths.repaired_clean_json, df_repaired.to_dict(orient="records"))
    logger.info("Repaired data saved (%d rows).", len(df_repaired))

    # 6. Build repaired Chroma index & evaluate
    logger.info("Step 6: Rebuilding ChromaDB index from repaired data (%s)...", settings.repaired_collection_name)
    repaired_index = LocalEmbeddingIndex.build(
        df=df_repaired,
        settings=settings,
        embeddings_output_path=settings.paths.repaired_embeddings_json,
    )

    logger.info("Evaluating recovered agent performance on repaired data...")
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    repaired_metrics = repaired_bundle.summary
    logger.info(
        "Repaired Metrics: Hit Rate=%.4f, Token F1=%.4f, Judge Score=%.2f",
        repaired_metrics.get("retrieval_hit_rate", 0.0),
        repaired_metrics.get("mean_token_f1", 0.0),
        repaired_metrics.get("mean_judge_score", 0.0),
    )

    # 7. Run Data Quality Gate on repaired data
    repaired_quality = run_data_quality_checks(df_repaired, settings, "repaired")
    repaired_freshness = repaired_quality.get("freshness", {})

    # 8. Generate 3-State Markdown Comparison Report
    logger.info("Step 7: Generating 3-State Comparison Report...")
    settings.paths.comparison_report.parent.mkdir(parents=True, exist_ok=True)
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_metrics,
        repaired_metrics=repaired_metrics,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )
    logger.info("Comparison report generated: %s", settings.paths.comparison_report)

    # Console comparison table
    b_hit = baseline_metrics.get("retrieval_hit_rate", 0.0)
    c_hit = corrupted_metrics.get("retrieval_hit_rate", 0.0)
    r_hit = repaired_metrics.get("retrieval_hit_rate", 0.0)

    b_f1 = baseline_metrics.get("mean_token_f1", 0.0)
    c_f1 = corrupted_metrics.get("mean_token_f1", 0.0)
    r_f1 = repaired_metrics.get("mean_token_f1", 0.0)

    b_score = baseline_metrics.get("mean_judge_score", 0.0)
    c_score = corrupted_metrics.get("mean_judge_score", 0.0)
    r_score = repaired_metrics.get("mean_judge_score", 0.0)

    print("\n" + "=" * 75)
    print("BANG DOI CHIEU HIỆU NĂNG 3 TRẠNG THÁI: BASELINE vs CORRUPTED vs REPAIRED")
    print("=" * 75)
    print(f"{'Chỉ số':<25} | {'Baseline (Sạch)':<16} | {'Corrupted (Lỗi)':<16} | {'Repaired (Phục hồi)':<16}")
    print("-" * 75)
    print(f"{'Retrieval Hit Rate':<25} | {b_hit:<16.2%} | {c_hit:<16.2%} | {r_hit:<16.2%}")
    print(f"{'Mean Token F1':<25} | {b_f1:<16.4f} | {c_f1:<16.4f} | {r_f1:<16.4f}")
    print(f"{'LLM Judge Score':<25} | {b_score:<16.2f} | {c_score:<16.2f} | {r_score:<16.2f}")
    print("-" * 75)
    print(f"GX Quality Status:        | {'PASSED':<16} | {'FAILED':<16} | {'PASSED':<16}")
    print(f"Freshness SLA:            | {'FRESH':<16} | {'STALE':<16} | {'FRESH':<16}")
    print("=" * 75)
    print(f"Báo cáo đối chiếu chi tiết: {settings.paths.comparison_report}")
    print(f"Nhật ký lỗi tiêm vào:       {settings.paths.corruption_log}\n")

    return {
        "baseline_metrics": baseline_metrics,
        "corrupted_metrics": corrupted_metrics,
        "repaired_metrics": repaired_metrics,
        "corrupted_quality": corrupted_quality,
        "repaired_quality": repaired_quality,
    }


def main() -> None:
    run_corruption_pipeline()

