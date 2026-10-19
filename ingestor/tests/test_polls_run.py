"""Run documents for the polls real load (report and source section).

The live state of the local ``silver``/``bronze`` load is operational evidence:
the commands and reproducible SQL live in ``docs/ingestor/polls-run.md`` and
``progress/impl_polls_run.md``. These tests only pin the versioned documents,
so they need neither ``data/raw/`` nor Postgres.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


# --- Run report (T3: R7-R11) -----------------------------------------------


def _report() -> str:
    return (REPO_ROOT / "docs" / "ingestor" / "polls-run.md").read_text(
        encoding="utf-8"
    )


def test_docs_polls_run_completeness():  # R7, R8, R9, R10
    text = _report()
    for needle in (
        "fetch-polls",
        "ingest-polls",
        "Completitud",
        "584",
        "cabecera",
        "separadora",
        "resultado",
        "Lead",
        "Fuera de alcance",
        "FA",
        "66–67",  # U+2013: the adapter warning literal
        "select count(*)",
        "silver.poll",
        "silver.poll_result",
        "bronze.ingestion",
        "revision_id",
        "oldid=",
    ):
        assert needle in text


def test_docs_polls_run_cotejo():  # R11
    section = _report().split("## Cotejo", 1)[1].split("\n## ", 1)[0]
    rows = [
        line
        for line in section.splitlines()
        if line.startswith("|") and "%" in line and "escañ" in line
    ]
    assert len(rows) >= 5


# --- Source section (T5: R12-R15) ------------------------------------------


def _data_sources() -> str:
    return (REPO_ROOT / ".agents" / "data-sources.md").read_text(encoding="utf-8")


def test_docs_data_sources():  # R12, R15
    text = _data_sources()
    for needle in (
        "Sondeos (Wikipedia)",
        "Opinion polling for the 2026 Spanish general election",
        "wikitext",
        "{revid}.wikitext",
        "data/raw/polls/wikipedia-en/2026-general/",
        "fetch-polls",
        "ingest-polls",
        "polls-run.md",
        "../docs/ingestor/polls-run.md",
        "CC BY-SA",
        "oldid=",
    ):
        assert needle in text
    # the relative link from .agents/ must not climb out of the repo
    assert "../../docs/ingestor/polls-run.md" not in text


def test_docs_data_sources_quirks():  # R13, R14
    text = _data_sources()
    for needle in (
        "rowspan",
        "CIS",
        "cabecera",
        "2026 (after FA)",
        "separador",
        "resultado",
        "Lead",
        "cruce de año",
        "<2.0",
        "fecha de publicación",
        "participación",
    ):
        assert needle in text
