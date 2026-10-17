"""Fetch the fixed-revision wikitext snapshot of the polls page.

The current revision is resolved through the MediaWiki API and the wikitext
is downloaded from ``index.php?oldid=…&action=raw``, so the snapshot is
pinned to a revision. Stdlib only (``urllib``); no database.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from pathlib import Path
from typing import IO, NamedTuple
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ingestor.errors import IngestError

logger = logging.getLogger(__name__)

Opener = Callable[..., IO[bytes]]  # compatible with urllib.request.urlopen

DEFAULT_PAGE = "Opinion polling for the 2026 Spanish general election"
DEFAULT_SNAPSHOT_DIR = "2026-general"
SOURCE = "wikipedia-en"
API_URL = "https://en.wikipedia.org/w/api.php"
RAW_URL = "https://en.wikipedia.org/w/index.php"
USER_AGENT = "votoscope-ingestor/0.1 (https://github.com/javidevmar/votoscope)"
TIMEOUT_SECONDS = 30
ATTEMPTS = 2  # the initial attempt plus one retry


class FetchOutcome(NamedTuple):
    """Result of a fetch: resolved revision, snapshot path and whether it was downloaded."""

    revid: int
    timestamp: str
    path: Path
    downloaded: bool


def parse_revision_response(payload: bytes) -> tuple[int, str]:
    """Return ``(revid, timestamp)`` of the first page's current revision."""
    data = json.loads(payload)
    pages = data.get("query", {}).get("pages") or []
    page = pages[0] if pages else {}
    revisions = page.get("revisions") or []
    if page.get("missing") or not revisions:
        raise IngestError("API response without a revision (missing page?)")
    revision = revisions[0]
    return revision["revid"], revision["timestamp"]


def snapshot_dir(page: str) -> str:
    """Snapshot folder for ``page``: ``2026-general`` or a slug of the title."""
    if page.replace("_", " ") == DEFAULT_PAGE:
        return DEFAULT_SNAPSHOT_DIR
    return re.sub(r"[^a-z0-9]+", "-", page.lower()).strip("-")


def snapshot_path(page: str, revid: int, raw_dir: Path) -> Path:
    """Bronze path of a snapshot: ``<raw_dir>/polls/<source>/<dir>/<revid>.wikitext``."""
    return raw_dir / "polls" / SOURCE / snapshot_dir(page) / f"{revid}.wikitext"


def _api_url(page: str) -> str:
    """Resolution URL: current revision id and timestamp for ``page``."""
    params = {
        "action": "query",
        "prop": "revisions",
        "rvprop": "ids|timestamp",
        "redirects": "1",
        "format": "json",
        "formatversion": "2",
        "titles": page,
    }
    return f"{API_URL}?{urlencode(params)}"


def _raw_url(revid: int) -> str:
    """Download URL of a fixed revision: canonical wikitext, not HTML."""
    return f"{RAW_URL}?{urlencode({'oldid': revid, 'action': 'raw'})}"


def _request(url: str, opener: Opener | None) -> bytes:
    """GET ``url`` with the project User-Agent, a timeout and one retry."""
    opener = opener or urlopen
    request = Request(url, headers={"User-Agent": USER_AGENT})
    last_error: OSError | None = None
    for attempt in range(ATTEMPTS):
        try:
            with opener(request, timeout=TIMEOUT_SECONDS) as response:
                return response.read()
        except OSError as error:
            last_error = error
            if attempt + 1 < ATTEMPTS:
                logger.warning("request failed (%s); retrying once", url)
    raise IngestError(
        f"request failed after {ATTEMPTS} attempts: {url}"
    ) from last_error


def resolve_revision(page: str, opener: Opener | None = None) -> tuple[int, str]:
    """Resolve the current revision of ``page`` as ``(revid, timestamp)``."""
    revid, timestamp = parse_revision_response(_request(_api_url(page), opener))
    logger.info("resolved page=%s revid=%s timestamp=%s", page, revid, timestamp)
    return revid, timestamp


def download_wikitext(revid: int, opener: Opener | None = None) -> bytes:
    """Download the wikitext of a fixed revision."""
    return _request(_raw_url(revid), opener)


def fetch_snapshot(
    page: str = DEFAULT_PAGE, *, raw_dir: Path, opener: Opener | None = None
) -> FetchOutcome:
    """Resolve, download and store the snapshot of ``page``'s current revision."""
    revid, timestamp = resolve_revision(page, opener)
    path = snapshot_path(page, revid, raw_dir)
    if path.exists():
        logger.info("snapshot up to date: %s", path)
        return FetchOutcome(revid, timestamp, path, downloaded=False)
    data = download_wikitext(revid, opener)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    logger.info("downloaded snapshot %s", path)
    return FetchOutcome(revid, timestamp, path, downloaded=True)
