from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from x_algorithm_auditor.algorithm.parser import build_snapshot
from x_algorithm_auditor.algorithm.snapshot import AlgorithmSnapshot, write_snapshot

RUNTIME = Path(__file__).parent / "runtime"


def representative_param_source(mode: str = "weighted") -> str:
    declarations = {
        "FavoriteWeight": "0.5",
        "ReplyWeight": "5.0",
        "RetweetWeight": "1.0",
        "QuoteWeight": "5.0",
        "ShareWeight": "2.0",
        "ShareViaDmWeight": "5.0",
        "ShareViaCopyLinkWeight": "20.0",
        "FollowAuthorWeight": "4.0",
        "NotInterestedWeight": "-43.2",
        "BlockAuthorWeight": "-31.2",
        "MuteAuthorWeight": "-58.8",
        "ReportWeight": "-234.0",
        "OpenLinkWeight": "0.2",
        "ClickWeight": "0.4",
        "PhotoExpandWeight": "0.05",
        "ProfileClickWeight": "0.0",
        "FutureWeight": "0.42",
    }
    lines = ["// last sync 2026-08-12T04:09:22Z"]
    for symbol, default in declarations.items():
        lines.extend(
            [
                "param!(",
                f"    {symbol}: f64 = {default},",
                f'    "{symbol.lower()}"',
                ");",
            ]
        )
    lines.extend(
        [
            "param!(",
            f'    ValueModelMode: String = "{mode}",',
            '    "value_model_mode"',
            ");",
        ]
    )
    return "\n".join(lines)


def representative_ranking_source() -> str:
    names = [
        "FavoriteWeight",
        "ReplyWeight",
        "RetweetWeight",
        "QuoteWeight",
        "ShareWeight",
        "ShareViaDmWeight",
        "ShareViaCopyLinkWeight",
        "FollowAuthorWeight",
        "NotInterestedWeight",
        "BlockAuthorWeight",
        "MuteAuthorWeight",
        "ReportWeight",
        "OpenLinkWeight",
        "ClickWeight",
        "PhotoExpandWeight",
        "ProfileClickWeight",
    ]
    return "fn weighted() { let _ = (" + ", ".join(names) + "); }"


@pytest.fixture
def snapshot() -> AlgorithmSnapshot:
    return build_snapshot(
        parameter_source=representative_param_source(),
        ranking_source=representative_ranking_source(),
        commit_sha="a" * 40,
    )


@pytest.fixture
def cached_snapshot_dir(snapshot: AlgorithmSnapshot) -> Path:
    directory = RUNTIME / "snapshot-cache"
    directory.mkdir(parents=True, exist_ok=True)
    write_snapshot(snapshot, directory)
    return directory


@pytest.fixture
def synthetic_export() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for index in range(10):
        impressions = 100 + index * 50
        rows.append(
            {
                "Post ID": f"p{index}",
                "Post Text": f"Synthetic test post {index}",
                "Created At": f"2026-01-{index + 1:02d}T12:00:00Z",
                "Post Type": "Post",
                "Impressions": impressions,
                "Likes": index,
                "Replies": index % 4,
                "Reposts": index % 3,
                "Quotes": index % 2,
                "Shares": index % 3,
                "Bookmarks": index % 2,
                "Profile Visits": index + 1,
                "Follows": index % 3,
                "Link Clicks": index + 2,
                "Detail Expands": index + 3,
            }
        )
    rows.append(
        {
            "Post ID": "tiny",
            "Post Text": "Three impressions, one reply",
            "Created At": "2026-02-01T12:00:00Z",
            "Post Type": "Post",
            "Impressions": 3,
            "Likes": 0,
            "Replies": 1,
            "Reposts": 0,
            "Quotes": 0,
            "Shares": 0,
            "Bookmarks": 0,
            "Profile Visits": 0,
            "Follows": 0,
            "Link Clicks": 0,
            "Detail Expands": 0,
        }
    )
    rows.append(
        {
            "Post ID": "zero-impressions",
            "Post Text": "No exposure yet",
            "Created At": "2026-02-02T12:00:00Z",
            "Post Type": "Post",
            "Impressions": 0,
            "Likes": 0,
            "Replies": 0,
            "Reposts": 0,
            "Quotes": 0,
            "Shares": 0,
            "Bookmarks": 0,
            "Profile Visits": 0,
            "Follows": 0,
            "Link Clicks": 0,
            "Detail Expands": 0,
        }
    )
    return pd.DataFrame(rows)


@pytest.fixture
def synthetic_csv(synthetic_export: pd.DataFrame) -> Path:
    path = RUNTIME / "analytics.csv"
    synthetic_export.to_csv(path, index=False, encoding="utf-8")
    return path


@pytest.fixture
def synthetic_xlsx(synthetic_export: pd.DataFrame) -> Path:
    path = RUNTIME / "analytics.xlsx"
    synthetic_export.to_excel(path, index=False)
    return path


@pytest.fixture
def detector_rich_export() -> pd.DataFrame:
    """Synthetic account cohort with one qualifying flag of each detector type."""

    impressions = [3, 20, 40, 60, 100, 120, 150, 180, 220, 300, 500, 800, 1000, 1200]
    post_ids = [
        "tiny",
        "low-1",
        "low-2",
        "low-3",
        "under-winner",
        "tool-2",
        "tool-3",
        "news-1",
        "news-2",
        "comparison-1",
        "reply-1",
        "project-1",
        "social-1",
        "cheap-exposure",
    ]
    texts = [
        "tiny tool response",
        "low sample one",
        "low sample two",
        "low sample three",
        "How to use this tool: step by step tutorial",
        "Tool SDK hands-on notes",
        "API tool implementation notes",
        "AI news: model announced",
        "Breaking AI news update",
        "Tool A vs Tool B comparison",
        "A practical tool note",
        "Building an open source project",
        "Thanks community",
        "AI news: release notes",
    ]
    post_types = ["Post"] * len(post_ids)
    post_types[10] = "Reply"
    rows: list[dict[str, object]] = []
    for index, (post_id, exposure, text, post_type) in enumerate(
        zip(post_ids, impressions, texts, post_types, strict=True)
    ):
        action = 1 if index not in {4, 13} else 0
        row = {
            "Post ID": post_id,
            "Post Text": text,
            "Created At": f"2026-04-{index + 1:02d}T12:00:00Z",
            "Post Type": post_type,
            "Impressions": exposure,
            "Likes": action,
            "Replies": action,
            "Reposts": action,
            "Quotes": action,
            "Shares": action,
            "Bookmarks": action,
            "Profile Visits": action,
            "Follows": action,
            "Link Clicks": action,
            "Detail Expands": action,
        }
        if post_id == "tiny":
            row.update({"Likes": 0, "Replies": 1, "Profile Visits": 0, "Follows": 0})
        elif post_id == "under-winner":
            row.update(
                {
                    "Likes": 20,
                    "Replies": 10,
                    "Reposts": 5,
                    "Quotes": 2,
                    "Shares": 2,
                    "Bookmarks": 5,
                    "Profile Visits": 20,
                    "Follows": 10,
                    "Link Clicks": 5,
                    "Detail Expands": 10,
                }
            )
        elif post_id == "cheap-exposure":
            row.update(
                {
                    "Likes": 0,
                    "Replies": 0,
                    "Reposts": 0,
                    "Quotes": 0,
                    "Shares": 0,
                    "Bookmarks": 0,
                    "Profile Visits": 0,
                    "Follows": 0,
                    "Link Clicks": 0,
                    "Detail Expands": 0,
                }
            )
        rows.append(row)
    return pd.DataFrame(rows)


@pytest.fixture
def detector_rich_csv(detector_rich_export: pd.DataFrame) -> Path:
    path = RUNTIME / "detector-rich.csv"
    detector_rich_export.to_csv(path, index=False, encoding="utf-8")
    return path


@pytest.fixture
def detector_rich_xlsx(detector_rich_export: pd.DataFrame) -> Path:
    path = RUNTIME / "detector-rich.xlsx"
    detector_rich_export.to_excel(path, index=False)
    return path
