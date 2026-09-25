from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any

import pandas as pd

from core.config import Settings, load_settings
from core.utils import write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set, load_or_create_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run_phase1_pipeline(settings: Settings | None = None) -> dict[str, Any]:
    """Execute the end-to-end Phase 1 Baseline Pipeline."""
    if settings is None:
        settings = load_settings()

    logger.info("=== Starting Phase 1: Baseline Pipeline ===")

    # 1. Load or fetch raw records
    logger.info("Step 1: Ingesting raw paper records...")
    records = fetch_source_records(settings)
    if not records and settings.paths.raw_records_json.exists():
        records = load_raw_records(settings.paths.raw_records_json)
    logger.info("Loaded %d raw paper records.", len(records))

    # 2. Clean data
    logger.info("Step 2: Cleaning and normalizing data...")
    run_date = datetime.now(timezone.utc)
    df = build_clean_dataframe(records, run_date)
    logger.info("Cleaned %d records.", len(df))

    # Save clean artifacts (CSV and JSON)
    settings.paths.clean_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(settings.paths.clean_csv, index=False)
    write_json(settings.paths.clean_json, df.to_dict(orient="records"))
    logger.info("Saved clean CSV: %s", settings.paths.clean_csv)
    logger.info("Saved clean JSON: %s", settings.paths.clean_json)

    # 3. Build Chroma index
    logger.info("Step 3: Building ChromaDB vector index...")
    settings.paths.chroma_dir.mkdir(parents=True, exist_ok=True)
    settings.paths.embeddings_json.parent.mkdir(parents=True, exist_ok=True)
    index = LocalEmbeddingIndex.build(
        df=df,
        settings=settings,
        embeddings_output_path=settings.paths.embeddings_json,
    )
    logger.info(
        "ChromaDB index built with %d documents in collection '%s'.",
        len(index.documents),
        index.collection_name,
    )

    # 4. Load or create evaluation set
    logger.info("Step 4: Loading or creating benchmark evaluation test set...")
    settings.paths.eval_testset.parent.mkdir(parents=True, exist_ok=True)
    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        test_set = build_test_set(df, output_path=settings.paths.eval_testset)
        logger.info("Built fresh test set with %d questions.", len(test_set))
    else:
        test_set = load_or_create_test_set(df, test_set_path=settings.paths.eval_testset)
        logger.info("Loaded existing test set with %d questions.", len(test_set))

    # 5. Evaluate pipeline
    logger.info("Step 5: Evaluating baseline retrieval & agent performance...")
    settings.paths.baseline_metrics.parent.mkdir(parents=True, exist_ok=True)
    settings.paths.baseline_answers.parent.mkdir(parents=True, exist_ok=True)
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    metrics = bundle.summary
    logger.info(
        "Baseline Metrics: Hit Rate=%.4f, Token F1=%.4f, Judge Score=%.2f",
        metrics.get("retrieval_hit_rate", 0.0),
        metrics.get("mean_token_f1", 0.0),
        metrics.get("mean_judge_score", 0.0),
    )

    # 6. Run data quality checks & freshness report
    logger.info("Step 6: Running Great Expectations 1.x & Freshness SLA checks...")
    quality_result = run_data_quality_checks(df, settings, "baseline")
    logger.info(
        "Quality checks finished: GX Success=%s, Fresh=%s, Overall=%s",
        quality_result.get("gx_success"),
        quality_result.get("is_fresh"),
        quality_result.get("success"),
    )

    # 7. Generate markdown report
    logger.info("Step 7: Generating Phase 1 Markdown report...")
    settings.paths.baseline_report.parent.mkdir(parents=True, exist_ok=True)
    source_summary = {
        "total_records": len(df),
        "source_api": settings.source_api,
        "source_query": settings.source_query,
        "source_filter": settings.source_filter,
        "clean_csv_path": str(settings.paths.clean_csv),
        "clean_json_path": str(settings.paths.clean_json),
        "chroma_dir": str(settings.paths.chroma_dir),
        "collection_name": settings.baseline_collection_name,
    }
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=metrics,
        quality=quality_result,
        freshness=quality_result.get("freshness", {}),
    )
    logger.info("Phase 1 report generated: %s", settings.paths.baseline_report)

    # Final summary display
    print("\n" + "=" * 65)
    print("PHASE 1 BASELINE PIPELINE HOAN THANH XUAT SAC!")
    print("=" * 65)
    print("Artifacts da sinh ra trong thu muc data/:")
    print(f" 1. Cleaned CSV:      {settings.paths.clean_csv}")
    print(f" 2. ChromaDB Index:   {settings.paths.chroma_dir} (Collection: {settings.baseline_collection_name})")
    print(f" 3. Test Set:         {settings.paths.eval_testset} ({len(test_set)} cau hoi)")
    print(f" 4. Baseline Metrics: {settings.paths.baseline_metrics}")
    print(f"    - Retrieval Hit Rate: {metrics.get('retrieval_hit_rate', 0.0):.2%}")
    print(f"    - Mean Token F1:      {metrics.get('mean_token_f1', 0.0):.4f}")
    print(f"    - LLM Judge Score:    {metrics.get('mean_judge_score', 0.0):.2f}/5.0")
    print(f" 5. Phase 1 Report:   {settings.paths.baseline_report}")
    print("=" * 65 + "\n")

    return {
        "df": df,
        "index": index,
        "metrics": metrics,
        "quality": quality_result,
    }


def main() -> None:
    run_phase1_pipeline()

