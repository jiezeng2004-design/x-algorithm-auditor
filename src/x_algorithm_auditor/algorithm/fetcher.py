"""Commit-pinned public GitHub acquisition with honest validated cache fallback."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from x_algorithm_auditor.algorithm.parser import build_snapshot
from x_algorithm_auditor.algorithm.snapshot import (
    AlgorithmSnapshot,
    diff_snapshots,
    latest_valid_snapshot,
    write_snapshot,
)


class AlgorithmSourceError(RuntimeError):
    """Raised when neither live public source nor a valid cache is available."""


@dataclass(frozen=True)
class FetchResult:
    snapshot: AlgorithmSnapshot
    snapshot_path: Path | None
    used_cache: bool


class GitHubAlgorithmFetcher:
    """Fetch a consistent set of official source files by resolved full SHA."""

    repository = "xai-org/x-algorithm"
    parameter_path = "home-mixer/params/param.rs"
    ranking_path = "home-mixer/scorers/ranking_scorer.rs"

    def __init__(self, timeout_seconds: float = 20.0) -> None:
        self.timeout_seconds = timeout_seconds

    def _get_bytes(self, url: str) -> bytes:
        request = Request(url, headers={"User-Agent": "x-algorithm-auditor/0.1"})
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310 - fixed HTTPS URLs
                return response.read()
        except (HTTPError, URLError, OSError) as error:
            raise AlgorithmSourceError(f"unable to fetch {url}: {error}") from error

    def resolve_commit(self, branch: str = "main") -> str:
        """Resolve a branch using GitHub's commit endpoint before any source fetch."""

        url = f"https://api.github.com/repos/{self.repository}/commits/{branch}"
        try:
            payload = json.loads(self._get_bytes(url).decode("utf-8"))
            sha = str(payload["sha"]).lower()
        except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise AlgorithmSourceError(
                f"invalid commit response for branch {branch}: {error}"
            ) from error
        if not re.fullmatch(r"[0-9a-f]{40}", sha):
            raise AlgorithmSourceError(
                f"branch {branch} did not resolve to a full 40-character SHA"
            )
        return sha

    def fetch_text_at_commit(self, commit_sha: str, path: str) -> str:
        """Fetch exact source bytes by immutable commit SHA, never by moving branch."""

        url = f"https://raw.githubusercontent.com/{self.repository}/{commit_sha}/{path}"
        try:
            return self._get_bytes(url).decode("utf-8")
        except UnicodeDecodeError as error:
            raise AlgorithmSourceError(f"source at {path} is not UTF-8: {error}") from error

    def fetch_live_snapshot(self, branch: str = "main") -> AlgorithmSnapshot:
        """Resolve, fetch, and parse a consistent public snapshot."""

        commit_sha = self.resolve_commit(branch)
        parameter_source = self.fetch_text_at_commit(commit_sha, self.parameter_path)
        try:
            ranking_source = self.fetch_text_at_commit(commit_sha, self.ranking_path)
        except AlgorithmSourceError:
            ranking_source = None
        return build_snapshot(
            parameter_source=parameter_source,
            ranking_source=ranking_source,
            commit_sha=commit_sha,
            branch=branch,
            repository=self.repository,
            parameter_path=self.parameter_path,
            ranking_path=self.ranking_path,
        )


class SnapshotProvider:
    """Obtain a live snapshot or the newest validated local cache with provenance."""

    def __init__(self, fetcher: GitHubAlgorithmFetcher | None = None) -> None:
        self.fetcher = fetcher or GitHubAlgorithmFetcher()

    def acquire(
        self,
        snapshot_dir: Path,
        *,
        branch: str = "main",
        offline: bool = False,
    ) -> FetchResult:
        """Acquire source evidence; no bundled values are ever substituted as live."""

        previous_item = latest_valid_snapshot(snapshot_dir)
        previous = previous_item[0] if previous_item else None
        if not offline:
            try:
                snapshot = self.fetcher.fetch_live_snapshot(branch)
                snapshot = snapshot.model_copy(
                    update={"change_from_previous": diff_snapshots(previous, snapshot)}
                )
                path = write_snapshot(snapshot, snapshot_dir)
                return FetchResult(snapshot=snapshot, snapshot_path=path, used_cache=False)
            except AlgorithmSourceError as error:
                live_error = str(error)
        else:
            live_error = "offline/cache-only mode requested"

        if previous_item is None:
            raise AlgorithmSourceError(
                f"official algorithm source unavailable ({live_error}) and no valid cached snapshot exists in {snapshot_dir}"
            )
        cached, path = previous_item
        warning = f"Algorithm source: cached ({live_error}); snapshot commit: {cached.commit_sha}"
        return FetchResult(
            snapshot=cached.with_cached_mode(warning), snapshot_path=path, used_cache=True
        )
