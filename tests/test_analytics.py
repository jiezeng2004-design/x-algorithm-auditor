from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from x_algorithm_auditor.analytics.deduplicate import deduplicate_posts
from x_algorithm_auditor.analytics.loader import (
    CROSS_EXPORT_WARNING,
    AnalyticsLoadError,
    load_analytics,
)
from x_algorithm_auditor.analytics.schema import AnalyticsSchemaError, map_headers

from .conftest import RUNTIME


def test_csv_and_xlsx_normalize_equivalently(synthetic_csv: Path, synthetic_xlsx: Path) -> None:
    csv = load_analytics(synthetic_csv)
    xlsx = load_analytics(synthetic_xlsx)
    columns = ["post_id", "impressions", "likes", "replies", "profile_visits", "follows"]
    pd.testing.assert_frame_equal(csv.data[columns], xlsx.data[columns], check_dtype=False)
    assert "absent_column:source_file" not in csv.quality.events
    assert "absent_column:source_row" not in csv.quality.events


@pytest.mark.parametrize("suffix", [".xls", ".xlsm"])
def test_legacy_excel_extensions_fail_with_actionable_csv_xlsx_contract(suffix: str) -> None:
    path = RUNTIME / f"unsupported-input{suffix}"
    path.write_text("legacy workbook content is intentionally unsupported", encoding="utf-8")
    with pytest.raises(AnalyticsLoadError) as error:
        load_analytics(path)
    assert str(error.value) == (
        f"unsupported input format {suffix!r}; only .csv and .xlsx are supported"
    )


def test_explicit_alias_map_maps_safe_unknown_header() -> None:
    export = pd.DataFrame({"Identifier": ["x"], "Exposure count": [100], "Likes": [0]})
    input_path = RUNTIME / "custom.csv"
    alias_path = RUNTIME / "aliases.yaml"
    export.to_csv(input_path, index=False)
    alias_path.write_text("Identifier: post_id\nExposure count: impressions\n", encoding="utf-8")
    loaded = load_analytics(input_path, alias_path)
    assert loaded.data.loc[0, "post_id"] == "x"
    assert loaded.data.loc[0, "impressions"] == 100
    assert loaded.data.loc[0, "likes"] == 0


def test_ambiguous_aliases_fail_instead_of_guessing() -> None:
    input_path = RUNTIME / "ambiguous.csv"
    pd.DataFrame({"Post ID": ["x"], "Impressions": [1], "Views": [2]}).to_csv(
        input_path, index=False
    )
    with pytest.raises(AnalyticsLoadError, match="ambiguous mapping"):
        load_analytics(input_path)


@pytest.mark.parametrize(
    "header",
    ["Post Link", "Post URL", "Tweet Link", "Tweet URL", "Status Link", "Status URL"],
)
def test_canonical_url_aliases_are_explicit_and_semantically_safe(header: str) -> None:
    mapped = map_headers([header])
    assert mapped.source_to_canonical == {header: "canonical_url"}
    assert mapped.unknown_headers == []


def test_generic_url_header_is_not_guessed_as_canonical_url() -> None:
    mapped = map_headers(["URL"])
    assert mapped.source_to_canonical == {}
    assert mapped.unknown_headers == ["URL"]


def test_multiple_canonical_url_aliases_still_fail_ambiguity_rejection() -> None:
    with pytest.raises(AnalyticsSchemaError, match="ambiguous mapping"):
        map_headers(["Post Link", "Status URL"])


def test_account_overview_export_is_rejected_with_cross_export_warning() -> None:
    input_path = RUNTIME / "account-overview.csv"
    pd.DataFrame(
        {
            "Date": ["2026-08-14"],
            "Impressions": [100],
            "Unfollows": [1],
            "Create Post": [2],
            "Video views": [3],
            "Media views": [4],
        }
    ).to_csv(input_path, index=False)
    with pytest.raises(AnalyticsLoadError) as error:
        load_analytics(input_path)
    assert CROSS_EXPORT_WARNING in str(error.value)
    assert "Provide a per-post Analytics export" in str(error.value)


def test_missing_zero_malformed_negative_and_zero_impression_remain_distinct() -> None:
    path = RUNTIME / "quality.csv"
    pd.DataFrame(
        {
            "Post ID": ["zero", "missing", "bad", "negative", "percent"],
            "Impressions": [0, 100, "bad", 100, "10%"],
            "Likes": [0, None, "bad", -1, "30%"],
            "Created At": ["bad-date", "2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"],
        }
    ).to_csv(path, index=False)
    loaded = load_analytics(path)
    frame = loaded.data
    assert frame.loc[0, "impressions"] == 0
    assert frame.loc[0, "likes"] == 0
    assert pd.isna(frame.loc[1, "likes"])
    assert pd.isna(frame.loc[2, "impressions"])
    assert pd.isna(frame.loc[2, "likes"])
    assert pd.isna(frame.loc[3, "likes"])
    assert pd.isna(frame.loc[4, "impressions"])
    assert loaded.quality.events["negative_count:likes"] == 1
    assert loaded.quality.events["percentage_for_count:likes"] == 1
    assert loaded.quality.events["malformed_timestamp:created_at"] == 1
    assert loaded.quality.events["missing_cell:likes"] == 1
    assert loaded.quality.events["absent_column:replies"] == 1
    assert loaded.quality.events["rate_unavailable:zero_impressions"] == 1
    assert loaded.quality.events["rate_unavailable:missing_or_invalid_impressions"] == 2
    assert loaded.quality.category_counts() == {
        "absent_columns": 23,
        "missing_cells": 1,
        "malformed_values": 5,
        "negative_values": 1,
        "rate_unavailable_zero_impressions": 1,
        "rate_unavailable_missing_or_invalid_impressions": 2,
    }


def test_multiple_date_ranges_are_reported() -> None:
    path = RUNTIME / "ranges.csv"
    pd.DataFrame(
        {
            "Post ID": ["a", "b"],
            "Impressions": [10, 20],
            "Date Range Start": ["2026-01-01", "2026-02-01"],
            "Date Range End": ["2026-01-31", "2026-02-28"],
        }
    ).to_csv(path, index=False)
    loaded = load_analytics(path)
    assert loaded.quality.events["multiple_date_ranges"] == 1


def test_deduplicate_hierarchy_never_sums_cumulative_metrics() -> None:
    path = RUNTIME / "duplicates.csv"
    pd.DataFrame(
        {
            "Post ID": ["same", "same", None, None, None, None],
            "Post URL": [
                None,
                None,
                "https://x.com/a/status/55",
                "https://x.com/b/status/55",
                None,
                None,
            ],
            "Post Text": [
                "same id",
                "same id",
                "same url",
                "same url",
                "same text",
                "fallback only",
            ],
            "Created At": [
                "2026-01-01",
                "2026-01-01",
                "2026-01-02",
                "2026-01-02",
                "2026-01-03",
                None,
            ],
            "Post Type": ["Post", "Post", "Post", "Post", "Post", "Post"],
            "Impressions": [100, 250, 20, 40, 60, 70],
            "Likes": [1, 3, 2, 4, 5, 6],
            "Export Date": [
                "2026-01-02",
                "2026-01-03",
                "2026-01-02",
                "2026-01-03",
                "2026-01-03",
                "2026-01-03",
            ],
        }
    ).to_csv(path, index=False)
    deduped = deduplicate_posts(load_analytics(path).data)
    assert deduped.summary.deduplicated_rows == 2
    assert len(deduped.data) == 4
    same = deduped.data.loc[deduped.data["post_id"] == "same"].iloc[0]
    assert same["impressions"] == 250
    assert same["likes"] == 3
    url = deduped.data.loc[deduped.data["canonical_url"].notna()].iloc[0]
    assert url["impressions"] == 40
    assert url["likes"] == 4
    assert deduped.summary.conflict_count >= 2


def test_deduplicate_uses_canonical_urls_and_preserves_weak_identities() -> None:
    path = RUNTIME / "canonical-and-weak-identities.csv"
    pd.DataFrame(
        {
            "Post ID": [None, None, None, None, None, None, None, None],
            "Post URL": [
                "https://WWW.Example.test/posts/alpha/?utm_source=one#fragment",
                "http://example.test/posts/alpha?campaign=two",
                None,
                None,
                None,
                None,
                None,
                None,
            ],
            "Post Text": [
                "first URL export",
                "later URL export with corrected text",
                "same short text",
                "same short text",
                "same timestamp text",
                " SAME timestamp text ",
                None,
                None,
            ],
            "Created At": [
                None,
                None,
                None,
                None,
                "2026-03-01T00:00:00Z",
                "2026-03-01T00:00:00Z",
                None,
                None,
            ],
            "Post Type": ["Post"] * 8,
            "Impressions": [10, 20, 30, 40, 50, 60, 70, 80],
            "Likes": [1, 2, 3, 4, 5, 6, 7, 8],
            "Export Date": [
                "2026-03-01",
                "2026-03-02",
                "2026-03-02",
                "2026-03-02",
                "2026-03-01",
                "2026-03-02",
                "2026-03-02",
                "2026-03-02",
            ],
        }
    ).to_csv(path, index=False)

    deduped = deduplicate_posts(load_analytics(path).data)
    assert len(deduped.data) == 6
    assert deduped.summary.deduplicated_rows == 2
    assert deduped.summary.insufficient_identity_rows == 4
    url_anchor = deduped.data.loc[deduped.data["dedup_identity_method"] == "canonical_url"].iloc[0]
    assert url_anchor["impressions"] == 20
    assert url_anchor["likes"] == 2
    weak = deduped.data.loc[deduped.data["dedup_identity_method"] == "insufficient_identity"]
    assert len(weak) == 4
    assert weak["dedup_identity_warning"].notna().all()
    assert set(weak["impressions"].tolist()) == {30.0, 40.0, 70.0, 80.0}
    text_timestamp = deduped.data.loc[
        deduped.data["dedup_identity_method"] == "text_timestamp"
    ].iloc[0]
    assert text_timestamp["impressions"] == 60
    assert text_timestamp["likes"] == 6


def test_header_normalization_handles_case_spacing_and_unicode() -> None:
    mapped = map_headers([" POST  ID ", "Impressions", "Ｐｒｏｆｉｌｅ　Ｖｉｓｉｔｓ"])
    assert mapped.source_to_canonical[" POST  ID "] == "post_id"
    assert mapped.source_to_canonical["Ｐｒｏｆｉｌｅ　Ｖｉｓｉｔｓ"] == "profile_visits"
