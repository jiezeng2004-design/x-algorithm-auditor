"""Local, deterministic, replaceable content-type classification."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import pandas as pd
import yaml

from x_algorithm_auditor._config_resources import default_config_label, read_default_config


@dataclass(frozen=True)
class ContentClassification:
    """Auditable result from a local classifier implementation."""

    content_type: str
    confidence: str
    reason: str
    version: str


class ContentClassifier(Protocol):
    """Replaceable classifier seam; implementations require no hosted model."""

    @property
    def version(self) -> str: ...

    def classify(self, *, text: object, post_type: object) -> ContentClassification: ...


def _normalized(value: object) -> str:
    if value is None or value is pd.NA or pd.isna(value):
        return ""
    return unicodedata.normalize("NFKC", str(value)).casefold().strip()


@dataclass(frozen=True)
class TaxonomyRule:
    content_type: str
    confidence: str
    keywords: tuple[str, ...]


@dataclass(frozen=True)
class ContentTaxonomy:
    version: str
    metadata_priority: tuple[TaxonomyRule, ...]
    rules: tuple[TaxonomyRule, ...]


def _parse_rules(payload: Any, *, default_confidence: str) -> tuple[TaxonomyRule, ...]:
    if not isinstance(payload, list):
        raise ValueError("content taxonomy rules must be a list")
    parsed: list[TaxonomyRule] = []
    for entry in payload:
        if not isinstance(entry, dict):
            raise ValueError("content taxonomy rule must be a mapping")
        content_type = entry.get("content_type")
        keywords = entry.get("keywords")
        confidence = entry.get("confidence", default_confidence)
        if not isinstance(content_type, str) or not isinstance(confidence, str):
            raise ValueError("content taxonomy rule needs string content_type and confidence")
        if not isinstance(keywords, list) or not all(isinstance(item, str) for item in keywords):
            raise ValueError("content taxonomy rule keywords must be strings")
        parsed.append(
            TaxonomyRule(
                content_type=content_type,
                confidence=confidence,
                keywords=tuple(_normalized(item) for item in keywords if _normalized(item)),
            )
        )
    return tuple(parsed)


def load_content_taxonomy(path: Path | None = None) -> ContentTaxonomy:
    """Load only explicit, generic keyword rules from a versioned local file."""

    try:
        if path is None:
            content, _ = read_default_config("content_taxonomy.yaml")
        else:
            content = path.read_text(encoding="utf-8")
        payload = yaml.safe_load(content)
    except (OSError, ValueError, yaml.YAMLError) as error:
        label = str(path) if path is not None else default_config_label("content_taxonomy.yaml")
        raise ValueError(f"unable to load content taxonomy {label}: {error}") from error
    if not isinstance(payload, dict) or not isinstance(payload.get("schema_version"), str):
        raise ValueError("content taxonomy requires a string schema_version")
    return ContentTaxonomy(
        version=str(payload["schema_version"]),
        metadata_priority=_parse_rules(payload.get("metadata_priority"), default_confidence="high"),
        rules=_parse_rules(payload.get("rules"), default_confidence="medium"),
    )


def extend_taxonomy_keywords(
    taxonomy: ContentTaxonomy, keyword_extensions: dict[str, list[str]]
) -> ContentTaxonomy:
    """Append explicit optional-preset keywords without changing metadata priority.

    Preset terms deliberately follow the generic rules. They can make a local
    taxonomy more useful, but cannot displace Reply/Quote/Thread metadata or
    alter generic score calculations and detector gates.
    """

    if not keyword_extensions:
        return taxonomy
    extensions = tuple(
        TaxonomyRule(
            content_type=content_type,
            confidence="preset",
            keywords=tuple(_normalized(keyword) for keyword in keywords if _normalized(keyword)),
        )
        for content_type, keywords in keyword_extensions.items()
    )
    return ContentTaxonomy(
        version=f"{taxonomy.version}+preset-keywords",
        metadata_priority=taxonomy.metadata_priority,
        rules=(*taxonomy.rules, *extensions),
    )


class DeterministicContentClassifier:
    """Ordered metadata and keyword rules; no external inference or personal preset."""

    def __init__(self, taxonomy: ContentTaxonomy | None = None) -> None:
        self._taxonomy = taxonomy or load_content_taxonomy()

    @property
    def version(self) -> str:
        return self._taxonomy.version

    def classify(self, *, text: object, post_type: object) -> ContentClassification:
        metadata = _normalized(post_type)
        for rule in self._taxonomy.metadata_priority:
            keyword = next((item for item in rule.keywords if item in metadata), None)
            if keyword is not None:
                return ContentClassification(
                    content_type=rule.content_type,
                    confidence=rule.confidence,
                    reason=f"metadata post_type matched {keyword!r}",
                    version=self.version,
                )

        normalized_text = _normalized(text)
        for rule in self._taxonomy.rules:
            keyword = next((item for item in rule.keywords if item in normalized_text), None)
            if keyword is not None:
                return ContentClassification(
                    content_type=rule.content_type,
                    confidence=rule.confidence,
                    reason=f"text keyword matched {keyword!r}",
                    version=self.version,
                )
        return ContentClassification(
            content_type="Other",
            confidence="low",
            reason="no configured metadata or keyword rule matched",
            version=self.version,
        )


def classify_posts(
    frame: pd.DataFrame, classifier: ContentClassifier | None = None
) -> pd.DataFrame:
    """Attach classifier evidence without changing Analytics or score semantics."""

    selected = classifier or DeterministicContentClassifier()
    output = frame.copy()
    results = [
        selected.classify(text=row.get("text"), post_type=row.get("post_type"))
        for _, row in output.iterrows()
    ]
    output["content_type"] = pd.Series(
        [result.content_type for result in results], index=output.index, dtype="string"
    )
    output["content_type_confidence"] = pd.Series(
        [result.confidence for result in results], index=output.index, dtype="string"
    )
    output["content_type_reason"] = pd.Series(
        [result.reason for result in results], index=output.index, dtype="string"
    )
    output["content_classifier_version"] = pd.Series(
        [result.version for result in results], index=output.index, dtype="string"
    )
    return output
