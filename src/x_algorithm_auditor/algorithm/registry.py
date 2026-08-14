"""Versioned relations between canonical Analytics fields and public parameters.

The registry deliberately separates a parsed upstream parameter from evidence
that a creator export observes the same behavior.  It contains no copied
third-party scoring formula and does not make a name-only mapping authoritative.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Relation = Literal["direct", "conditional", "approximate", "outcome", "unobservable"]


@dataclass(frozen=True)
class SignalRelation:
    """One public parameter to canonical Analytics relationship."""

    canonical_field: str
    parameter: str | None
    relation: Relation
    description: str


REGISTRY_VERSION = "source-relation-v1"

# The default registry intentionally excludes approximate source relationships
# from Alignment.  Adding a parser-supported parameter here never changes an
# existing export's scoring semantics without an explicit relation decision.
SIGNAL_RELATIONS: tuple[SignalRelation, ...] = (
    SignalRelation("likes", "FavoriteWeight", "direct", "Favorite action."),
    SignalRelation("replies", "ReplyWeight", "direct", "Reply action."),
    SignalRelation("reposts", "RetweetWeight", "direct", "Repost action."),
    SignalRelation("quotes", "QuoteWeight", "direct", "Quote action."),
    SignalRelation(
        "shares",
        "ShareWeight",
        "conditional",
        "Aggregate shares are used only where channel overlap is absent.",
    ),
    SignalRelation(
        "shares_via_dm",
        "ShareViaDmWeight",
        "direct",
        "Explicit share-via-DM action.",
    ),
    SignalRelation(
        "shares_via_copy_link",
        "ShareViaCopyLinkWeight",
        "direct",
        "Explicit share-via-copy-link action.",
    ),
    SignalRelation(
        "follows",
        "FollowAuthorWeight",
        "direct",
        "Post-attributed author follow where the export provides it.",
    ),
    SignalRelation(
        "not_interested", "NotInterestedWeight", "direct", "Explicit not-interested feedback."
    ),
    SignalRelation("blocks", "BlockAuthorWeight", "direct", "Explicit author block feedback."),
    SignalRelation("mutes", "MuteAuthorWeight", "direct", "Explicit author mute feedback."),
    SignalRelation("reports", "ReportWeight", "direct", "Explicit report feedback."),
    SignalRelation(
        "link_clicks",
        "OpenLinkWeight",
        "approximate",
        "Export link clicks are not automatically OpenLink scorer actions.",
    ),
    SignalRelation(
        "detail_expands",
        "ClickWeight",
        "approximate",
        "Detail expands are not assumed to be generic clicks.",
    ),
    SignalRelation(
        "media_views",
        "PhotoExpandWeight",
        "approximate",
        "Media views do not prove photo/video head semantics.",
    ),
    SignalRelation(
        "profile_visits",
        "ProfileClickWeight",
        "outcome",
        "Profile visits remain a creator-conversion outcome.",
    ),
    SignalRelation(
        "bookmarks",
        None,
        "unobservable",
        "No direct terminal weighted parameter is present in the reviewed default path; "
        "bookmarks are contextual only.",
    ),
)

EXPECTED_SIGNAL_PARAMETERS = frozenset(
    relation.parameter for relation in SIGNAL_RELATIONS if relation.parameter is not None
)


def relation_by_parameter() -> dict[str, list[SignalRelation]]:
    """Return every relation for a parameter, preserving the registry order."""

    result: dict[str, list[SignalRelation]] = {}
    for relation in SIGNAL_RELATIONS:
        if relation.parameter is None:
            continue
        result.setdefault(relation.parameter, []).append(relation)
    return result


def relation_by_field() -> dict[str, SignalRelation]:
    """Return the first relation for each canonical field."""

    return {relation.canonical_field: relation for relation in SIGNAL_RELATIONS}
