"""Repository documents: README and the closing coherence pass (feature 17).

Read-only checks over files in the repo: no network, no database.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(*parts: str) -> str:
    return REPO_ROOT.joinpath(*parts).read_text(encoding="utf-8")


def _relative_links(text: str) -> list[str]:
    """Targets of ``](target)`` that are not http(s)/mailto/anchor, no fragment."""
    targets = []
    for target in re.findall(r"\]\(([^)]+)\)", text):
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        targets.append(target.split("#", 1)[0])
    return targets


# --- README (T1: R1-R9) -----------------------------------------------------


def test_readme_project_summary():  # R1
    text = _read("README.md")
    for needle in (
        "Votoscope",
        "resultados electorales",
        "España",
        "Congreso",
        "resultados por mesa",
        "bronce",
        "plata",
        "oro",
        "silver",
        "gold",
        "Next.js",
    ):
        assert needle in text


def test_readme_prerequisites():  # R2
    text = _read("README.md")
    for needle in ("Docker", "uv", "Python"):
        assert needle in text


def test_readme_setup():  # R3
    text = _read("README.md")
    for needle in (
        "docker compose up -d --wait",
        "5434",
        "cd ingestor",
        "uv sync",
        "uv run alembic upgrade head",
        "uv run pytest",
    ):
        assert needle in text
    assert (
        text.index("docker compose up -d --wait")
        < text.index("uv sync")
        < text.index("uv run alembic upgrade head")
    )


def test_readme_data():  # R4
    text = _read("README.md")
    for needle in (
        "data/raw/congreso",
        "refs/ine",
        "uv run ingestor load-geography",
        "uv run ingestor ingest",
        "uv run ingestor fetch-polls",
        "uv run ingestor ingest-polls",
    ):
        assert needle in text


def test_readme_web_if_scaffolded():  # R5
    if not (REPO_ROOT / "web" / "package.json").exists():
        import pytest

        pytest.skip("web/ scaffold not present")
    text = _read("README.md")
    assert "web/" in text
    assert "gold" in text
    assert any(
        needle in text
        for needle in ("npm run dev", "pnpm dev", "bun run dev", "yarn dev", "next dev")
    )


def test_readme_attribution():  # R6, R7
    text = _read("README.md")
    for needle in (
        "infoelectoral.interior.gob.es",
        "Ministerio del Interior",
        "en.wikipedia.org",
        "Opinion polling for the 2026 Spanish general election",
        "CC BY-SA",
        "oldid=",
    ):
        assert needle in text


def test_readme_docs_links():  # R8
    text = _read("README.md")
    for needle in ("AGENTS.md", ".agents/", "docs/ingestor/ingesta.md"):
        assert needle in text


def test_readme_relative_links_resolve():  # R9
    for target in _relative_links(_read("README.md")):
        assert (REPO_ROOT / target).exists(), target


# --- Final status and coherence pass (T3: R10-R12) --------------------------


def test_status_document_current():  # R10
    text = _read(".agents", "status.md")
    assert re.search(r"Actualizado: \d{4}-\d{2}-\d{2}", text)
    for needle in ("README", "gold", "source_norm"):
        assert needle in text
    assert "listos para aprobar" not in text
    assert "pendiente en la web" not in text


def test_context_docs_coherent():  # R11
    architecture = _read(".agents", "architecture.md")
    assert "Pendiente de scaffold" not in architecture
    assert "Pendientes de crear" not in architecture
    environment = _read(".agents", "environment.md")
    assert "Pendiente de scaffold" not in environment
    assert "Vistas `gold`." not in _read("ingestor", "AGENTS.md")
    assert "Aún no hay scaffold" not in _read("web", "AGENTS.md")


def test_port_references():  # R12
    for parts in (
        ("README.md",),
        (".agents", "architecture.md"),
        ("ingestor", ".env.example"),
        ("docker-compose.yml",),
    ):
        assert "5433" not in _read(*parts), parts
    assert "5434" in _read("README.md")
    assert "5434" in _read("ingestor", ".env.example")
