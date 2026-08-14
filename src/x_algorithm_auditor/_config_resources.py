"""Read versioned default policy files from source or an installed wheel."""

from __future__ import annotations

from importlib import resources
from pathlib import Path


def _source_config_path(filename: str) -> Path:
    """Return the readable repository template path when running from source."""

    return Path(__file__).resolve().parents[2] / "config" / filename


def read_default_config(filename: str) -> tuple[str, str]:
    """Return default YAML content plus an honest provenance label.

    The root ``config/`` files are the editable source templates. Hatch copies
    those exact files into ``x_algorithm_auditor/resources`` during wheel
    building, so an installed command never relies on its original checkout.
    """

    source_path = _source_config_path(filename)
    if source_path.is_file():
        return source_path.read_text(encoding="utf-8"), str(source_path)

    try:
        resource = resources.files("x_algorithm_auditor").joinpath("resources", filename)
        return resource.read_text(encoding="utf-8"), f"package resource {resource}"
    except (FileNotFoundError, ModuleNotFoundError, OSError) as error:
        raise ValueError(
            f"default configuration {filename!r} is unavailable from source templates or package resources"
        ) from error


def default_config_label(filename: str) -> str:
    """Return the path/label used by the current runtime for diagnostics."""

    source_path = _source_config_path(filename)
    if source_path.is_file():
        return str(source_path)
    return f"package resource x_algorithm_auditor/resources/{filename}"
