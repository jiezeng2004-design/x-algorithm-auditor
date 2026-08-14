"""Parser for Rust ``param!`` declarations with source-drift diagnostics."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from x_algorithm_auditor.algorithm.registry import (
    EXPECTED_SIGNAL_PARAMETERS,
    relation_by_parameter,
)
from x_algorithm_auditor.algorithm.snapshot import (
    AlgorithmSnapshot,
    ExtractedSignal,
    ParsedParam,
    source_sha256,
    utc_now,
)


@dataclass
class ParseResult:
    """Complete parser evidence instead of an all-or-nothing result."""

    params: list[ParsedParam] = field(default_factory=list)
    unparsed: list[dict[str, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _macro_bodies(source: str) -> list[str]:
    """Extract balanced ``param!(...)`` bodies, independent of line layout."""

    bodies: list[str] = []
    marker = re.compile(r"\bparam!\s*\(")
    for match in marker.finditer(source):
        index = match.end()
        depth = 1
        quote: str | None = None
        escaped = False
        while index < len(source) and depth:
            char = source[index]
            if quote:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == quote:
                    quote = None
            elif char in {'"', "'"}:
                quote = char
            elif char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            index += 1
        if depth == 0:
            bodies.append(source[match.end() : index - 1])
    return bodies


def _split_top_level(body: str) -> list[str]:
    """Split macro arguments while leaving nested calls and quoted strings intact."""

    parts: list[str] = []
    start = 0
    depth = 0
    quote: str | None = None
    escaped = False
    for index, char in enumerate(body):
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in {'"', "'"}:
            quote = char
        elif char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        elif char == "," and depth == 0:
            parts.append(body[start:index].strip())
            start = index + 1
    final = body[start:].strip()
    if final:
        parts.append(final)
    return parts


def _clean_comment(value: str) -> str:
    return re.sub(r"//.*$|/\*.*?\*/", "", value, flags=re.DOTALL).strip().rstrip(";")


def _literal_from_text(value: str) -> tuple[str | None, float | None]:
    """Extract a safe scalar default; never coerce malformed numeric text to zero."""

    literal = _clean_comment(value).strip()
    if not literal:
        return None, None
    if literal.startswith('"') and literal.endswith('"'):
        return literal[1:-1], None
    if literal in {"true", "false"}:
        return literal, None
    number = literal.replace("_", "")
    try:
        return literal, float(number)
    except ValueError:
        return literal, None


def _parse_body(body: str) -> ParsedParam | None:
    """Parse common Rust macro shapes used by parameter declarations."""

    cleaned = _clean_comment(body)
    strings = re.findall(r'"((?:\\.|[^"\\])*)"', cleaned)
    config_key = strings[0] if strings else None

    # Supports ``Name: type = default`` and ``Name, type, \"key\", default``.
    assignment = re.search(
        r"\b([A-Za-z][A-Za-z0-9_]*)\s*(?::\s*([A-Za-z0-9_:<>]+))?\s*=\s*([^,;\n]+)",
        cleaned,
    )
    if assignment:
        symbol, rust_type, value = assignment.groups()
        literal, numeric = _literal_from_text(value)
        return ParsedParam(
            symbol=symbol,
            rust_type=rust_type,
            config_key=config_key,
            literal=literal,
            numeric_value=numeric,
            raw_macro=f"param!({body})",
        )

    parts = _split_top_level(cleaned)
    if not parts:
        return None
    first = re.match(r"\s*(?:pub(?:\s+const)?\s+)?([A-Za-z][A-Za-z0-9_]*)", parts[0])
    if not first:
        return None
    symbol = first.group(1)
    rust_type = None
    type_match = re.search(r":\s*([A-Za-z0-9_:<>]+)", parts[0])
    if type_match:
        rust_type = type_match.group(1)
    if rust_type is None and len(parts) > 1 and re.fullmatch(r"[A-Za-z0-9_:<>]+", parts[1]):
        rust_type = parts[1]

    # Positional production declarations have the shape
    # ``param!(Symbol, RustType, "config_key", default)``.  The default may
    # itself be a quoted string (for example ValueModelMode), so it must be
    # selected *after* the first config-key string instead of filtering all
    # quoted arguments away.
    config_index = next((index for index, part in enumerate(parts) if '"' in part), None)
    if config_index is not None and config_index < len(parts) - 1:
        candidate_values = parts[config_index + 1 :]
    else:
        candidate_values = [part for part in parts[1:] if '"' not in part]
        if not candidate_values and "=" not in cleaned:
            candidate_values = parts[1:]
    literal: str | None = None
    numeric: float | None = None
    if candidate_values:
        literal, numeric = _literal_from_text(candidate_values[-1])
    return ParsedParam(
        symbol=symbol,
        rust_type=rust_type,
        config_key=config_key,
        literal=literal,
        numeric_value=numeric,
        raw_macro=f"param!({body})",
    )


def parse_param_source(source: str) -> ParseResult:
    """Parse all reachable parameter macros and preserve malformed evidence."""

    result = ParseResult()
    bodies = _macro_bodies(source)
    if not bodies:
        result.warnings.append("no param! macro invocations were found")
    seen: set[str] = set()
    for body in bodies:
        parsed = _parse_body(body)
        if parsed is None:
            result.unparsed.append(
                {"reason": "unrecognized_param_macro", "raw_macro": f"param!({body})"}
            )
            continue
        if parsed.symbol in seen:
            result.warnings.append(f"duplicate param symbol parsed: {parsed.symbol}")
        seen.add(parsed.symbol)
        result.params.append(parsed)
        if (
            parsed.symbol.endswith("Weight")
            and parsed.literal is not None
            and parsed.numeric_value is None
        ):
            result.unparsed.append(
                {
                    "parameter": parsed.symbol,
                    "reason": "non_numeric_weight_default",
                    "literal": parsed.literal,
                }
            )
    return result


def _sync_timestamp(source: str) -> str | None:
    match = re.search(
        r"last\s+sync\s*[:=]?\s*(\d{4}-\d{2}-\d{2}T[0-9:.+-]+Z?)",
        source,
        re.IGNORECASE,
    )
    return match.group(1) if match else None


def _value_model_mode(params: list[ParsedParam]) -> str | None:
    for param in params:
        if param.symbol == "ValueModelMode" or param.config_key == "value_model_mode":
            return param.literal
    return None


def build_snapshot(
    *,
    parameter_source: str,
    ranking_source: str | None,
    commit_sha: str,
    branch: str = "main",
    repository: str = "xai-org/x-algorithm",
    parameter_path: str = "home-mixer/params/param.rs",
    ranking_path: str = "home-mixer/scorers/ranking_scorer.rs",
) -> AlgorithmSnapshot:
    """Build structured snapshot evidence from commit-pinned source bytes."""

    parsed = parse_param_source(parameter_source)
    params_by_symbol = {param.symbol: param for param in parsed.params}
    relations = relation_by_parameter()
    extracted: list[ExtractedSignal] = []
    active_values: list[bool] = []
    for parameter, linked in relations.items():
        param = params_by_symbol.get(parameter)
        if param is None:
            continue
        active: bool | None
        if ranking_source is None:
            active = None
        else:
            active = bool(re.search(rf"\b{re.escape(parameter)}\b", ranking_source))
            active_values.append(active)
        sign = "unknown"
        if param.numeric_value is not None:
            sign = (
                "positive"
                if param.numeric_value > 0
                else "negative"
                if param.numeric_value < 0
                else "zero"
            )
        for relation in linked:
            extracted.append(
                ExtractedSignal(
                    parameter=parameter,
                    canonical_field=relation.canonical_field,
                    relation=relation.relation,
                    numeric_value=param.numeric_value,
                    sign=sign,
                    active_scorer_reference=active,
                )
            )

    expected_missing = sorted(EXPECTED_SIGNAL_PARAMETERS - set(params_by_symbol))
    warnings = list(parsed.warnings)
    if expected_missing:
        warnings.append("expected parameters missing: " + ", ".join(expected_missing))
    if ranking_source is None:
        warnings.append("ranking scorer source unavailable; active-scorer coverage reduced")
    elif active_values and not all(active_values):
        inactive = sorted(
            signal.parameter for signal in extracted if signal.active_scorer_reference is False
        )
        warnings.append(
            "registered parameters not found in ranking source: "
            + ", ".join(dict.fromkeys(inactive))
        )
    mode = _value_model_mode(parsed.params)
    if mode is not None and mode != "weighted":
        warnings.append(f"ValueModelMode={mode!r}; weighted proxy compatibility is reduced")

    known = set(relations)
    unsupported = sorted(
        param.symbol
        for param in parsed.params
        if param.symbol.endswith("Weight") and param.symbol not in known
    )
    if unsupported:
        warnings.append(
            "unregistered weight parameters retained as context: " + ", ".join(unsupported)
        )
    if expected_missing and unsupported:
        warnings.append(
            "possible renamed or drifted weight parameters: expected names are missing while "
            "unregistered weight names are present"
        )
    ranking_hash = source_sha256(ranking_source) if ranking_source is not None else None
    return AlgorithmSnapshot(
        repository=repository,
        branch=branch,
        commit_sha=commit_sha,
        fetched_at_utc=utc_now(),
        parameter_source_path=parameter_path,
        ranking_source_path=ranking_path,
        parameter_sync_date=_sync_timestamp(parameter_source),
        source_sha256=source_sha256(parameter_source),
        ranking_source_sha256=ranking_hash,
        source_mode="live",
        value_model_mode=mode,
        extracted_signals=extracted,
        parsed_params=parsed.params,
        expected_missing=expected_missing,
        unsupported_params=unsupported,
        unparsed_params=parsed.unparsed,
        warnings=warnings,
        active_scorer_coverage=(sum(active_values) / len(active_values) if active_values else None),
        parameter_source_content=parameter_source,
        ranking_source_content=ranking_source,
    )
