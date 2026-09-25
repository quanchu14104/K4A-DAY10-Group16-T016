from pathlib import Path
from typing import Any, Sequence

import pandas as pd

from core.utils import first_sentence, read_json, write_json


class TestSet(list):
    """Benchmark test set wrapper that supports both list indexing and .samples access."""

    def __init__(self, samples: Sequence[dict[str, Any]]):
        super().__init__(samples)

    @property
    def samples(self) -> list[dict[str, Any]]:
        return list(self)


def build_test_set(
    df: pd.DataFrame,
    output_path: Path | str | None = None,
    num_questions: int = 5,
) -> TestSet:
    """Build a standard benchmark evaluation test set across 5 question types."""
    if len(df) < 2:
        raise ValueError("DataFrame must contain at least 2 papers to generate benchmark questions.")

    rows = df.to_dict(orient="records")
    samples: list[dict[str, Any]] = []

    # 1. Summary question
    row0 = rows[0]
    samples.append(
        {
            "id": "eval_001",
            "type": "summary",
            "question_type": "summary",
            "question": f"What is the summary of the paper '{row0['title']}'?",
            "ground_truth": first_sentence(row0["summary"]),
            "ground_truth_doc_ids": [str(row0["paper_id"])],
        }
    )

    # 2. Authors question
    row1 = rows[1 % len(rows)]
    samples.append(
        {
            "id": "eval_002",
            "type": "authors",
            "question_type": "authors",
            "question": f"Who are the authors of the research '{row1['title']}'?",
            "ground_truth": str(row1["authors_joined"]),
            "ground_truth_doc_ids": [str(row1["paper_id"])],
        }
    )

    # 3. Publication Date question
    row2 = rows[2 % len(rows)]
    samples.append(
        {
            "id": "eval_003",
            "type": "date",
            "question_type": "date",
            "question": f"When was the paper '{row2['title']}' published?",
            "ground_truth": str(row2["published"]),
            "ground_truth_doc_ids": [str(row2["paper_id"])],
        }
    )

    # 4. Category question
    row3 = rows[3 % len(rows)]
    samples.append(
        {
            "id": "eval_004",
            "type": "category",
            "question_type": "categories",
            "question": f"Which field or subject category does the paper '{row3['title']}' belong to?",
            "ground_truth": str(row3["categories_joined"]),
            "ground_truth_doc_ids": [str(row3["paper_id"])],
        }
    )

    # 5. Multi-hop question
    r_a = rows[0]
    r_b = rows[1 % len(rows)]
    samples.append(
        {
            "id": "eval_005",
            "type": "multi_hop",
            "question_type": "multi_hop",
            "question": (
                f"How do the principles in '{r_a['title']}' connect with the findings in '{r_b['title']}'?"
            ),
            "ground_truth": (
                f"'{r_a['title']}' addresses {r_a['primary_category']}, whereas '{r_b['title']}' "
                f"addresses {r_b['primary_category']}, collectively improving AI robustness."
            ),
            "ground_truth_doc_ids": [str(r_a["paper_id"]), str(r_b["paper_id"])],
        }
    )

    result_set = TestSet(samples[:num_questions])

    if output_path is not None:
        write_json(Path(output_path), list(result_set))

    return result_set


def load_or_create_test_set(
    df: pd.DataFrame,
    test_set_path: Path | str | None = None,
) -> TestSet:
    """Load existing benchmark test set from disk or create and persist a new one."""
    if test_set_path is not None:
        p = Path(test_set_path)
        if p.exists():
            data = read_json(p)
            return TestSet(data)

    return build_test_set(df, output_path=test_set_path)
