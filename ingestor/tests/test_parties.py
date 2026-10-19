"""Tests for the party catalogue and the shared party resolver.

No network and no database: the resolver is exercised with transient ``Party``
rows and the catalogue with TOML files under ``tmp_path`` (the bundled
catalogue is loaded through its default path).
"""

from __future__ import annotations

import ast
import logging
import sys
import tomllib
from pathlib import Path

import pytest

from ingestor import parties
from ingestor.errors import IngestError
from ingestor.models import Party
from ingestor.parties import (
    CATALOG_PATH,
    PartyResolver,
    load_catalog,
    normalize,
    slugify,
)

FIXTURES = Path(__file__).parent / "fixtures" / "party_catalog"

# The fifteen labels of the polls adapter (PARTY_COLUMNS), pinned to their slugs.
POLL_LABELS = {
    "PP": "pp",
    "PSOE": "psoe",
    "Vox": "vox",
    "Sumar": "sumar",
    "ERC": "erc",
    "Junts": "jxcat-junts",
    "EH Bildu": "eh-bildu",
    "PNV": "eaj-pnv",
    "BNG": "bng",
    "CCa": "cca",
    "UPN": "u-p-n",
    "Adelante Andalucía (2021)": "adelante-andalucia",
    "Podemos": "podemos",
    "SALF": "salf",
    "Aliança.cat": "alianca-cat",
}

# Dotted spelling / clean spelling of the same brand (diagnosis).
PUNCTUATION_PAIRS = [
    ("B.N.G.", "BNG"),
    ("P.P.", "PP"),
    ("P.S.O.E.", "PSOE"),
    ("C's", "Cs"),
    ("I.U.", "IU"),
    ("P.C.P.E.", "PCPE"),
    ("U.P.L.", "UPL"),
    ("F.I.A.", "FIA"),
    ("D.N.", "DN"),
    ("A.u.N.", "AUN"),
]

# Spellings of the brand families of the diagnosis (distinct curation decisions).
FAMILY_LABELS = [
    "podemos",
    "unidas podemos",
    "lv",
    "lve",
    "lv-gv",
    "verdes",
    "fe-de-las-j",
    "fe-de-las-jons",
    "fe-jons",
    "na",
    "na-bai",
    "erc",
    "esquerra",
    "erc-catsi",
]


def write_catalog(tmp_path: Path, text: str) -> Path:
    """Write a catalogue TOML under ``tmp_path`` and return its path."""
    path = tmp_path / "party_catalog.toml"
    path.write_text(text, encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("label", "key"),
    [
        ("B.N.G.", "BNG"),
        ("b.n.g.", "BNG"),
        ("C's", "CS"),
        ("C´s", "CS"),
        ("P. RIOJANO", "PRIOJANO"),
        ("EH Bildu", "EHBILDU"),
        ("Aliança.cat", "ALIANCACAT"),
        ("MÁS PAÍS", "MASPAIS"),
        ("España", "ESPANA"),
        ("Ç", "C"),
        ("JxCAT - JUNTS", "JXCATJUNTS"),
        ("  ", ""),
        ("...", ""),
    ],
)
def test_normalize_matrix(label: str, key: str) -> None:
    assert normalize(label) == key


# --- Catalogue: TOML loading, lookup and integrity (R2-R9) -------------------

SAMPLE_CATALOG = """
[parties.bng]
name = "BNG"
aliases = ["Bloque Nacionalista Galego"]

[parties.pp]
name = "PP"
"""


def test_catalog_loads_toml(tmp_path: Path) -> None:
    catalog = load_catalog(write_catalog(tmp_path, SAMPLE_CATALOG))
    assert {entry.slug for entry in catalog.entries} == {"bng", "pp"}
    bng = catalog.lookup("bng")
    assert bng is not None
    assert bng.name == "BNG"
    assert bng.aliases == ("Bloque Nacionalista Galego",)
    pp = catalog.lookup("pp")
    assert pp is not None
    assert pp.aliases == ()


def test_catalog_lookup_by_name_and_alias(tmp_path: Path) -> None:
    catalog = load_catalog(write_catalog(tmp_path, SAMPLE_CATALOG))
    assert catalog.lookup("BNG") is catalog.lookup("bng")
    assert catalog.lookup("b.n.g.") is catalog.lookup("bng")
    assert catalog.lookup("Bloque Nacionalista Galego") is catalog.lookup("bng")
    assert catalog.lookup("bloque.nacionalista.GALEGO") is catalog.lookup("bng")
    assert catalog.lookup("PP") is catalog.lookup("pp")


def test_catalog_lookup_unknown_returns_none(tmp_path: Path) -> None:
    catalog = load_catalog(write_catalog(tmp_path, SAMPLE_CATALOG))
    assert catalog.lookup("PPX") is None


def test_load_catalog_rejects_duplicate_key(tmp_path: Path) -> None:
    text = """
[parties.alfa]
name = "Alfa"
aliases = ["B.E.T.A."]

[parties.beta]
name = "Beta"
"""
    with pytest.raises(IngestError, match="BETA"):
        load_catalog(write_catalog(tmp_path, text))


def test_load_catalog_rejects_redundant_alias(tmp_path: Path) -> None:
    text = """
[parties.bng]
name = "BNG"
aliases = ["b.n.g."]
"""
    with pytest.raises(IngestError, match="bng"):
        load_catalog(write_catalog(tmp_path, text))


@pytest.mark.parametrize(
    "text",
    [
        '[parties.x]\nname = "..."\n',
        '[parties.x]\nname = "Equis"\naliases = ["---"]\n',
    ],
)
def test_load_catalog_rejects_key_without_alnum(tmp_path: Path, text: str) -> None:
    with pytest.raises(IngestError):
        load_catalog(write_catalog(tmp_path, text))


@pytest.mark.parametrize(
    "text",
    [
        None,  # missing file
        "[parties.bng\nname = 'BNG'\n",  # broken TOML
        '[parties.bng]\nname = "BNG"\n\n[parties.bng]\nname = "Otro"\n',  # repeated
        '[other]\nname = "x"\n',  # no [parties] table
    ],
)
def test_load_catalog_rejects_missing_file_and_bad_toml(
    tmp_path: Path, text: str | None
) -> None:
    path = tmp_path / "missing.toml" if text is None else write_catalog(tmp_path, text)
    with pytest.raises(IngestError, match=str(path.name)):
        load_catalog(path)


def test_load_catalog_rejects_entry_without_name(tmp_path: Path) -> None:
    text = """
[parties.x]
aliases = ["Equis"]
"""
    with pytest.raises(IngestError, match="'x'"):
        load_catalog(write_catalog(tmp_path, text))


# --- Bundled catalogue: coverage of the curated scope (R10-R15, R28) ---------


def test_catalog_loads_bundled() -> None:
    assert CATALOG_PATH.is_file()
    catalog = load_catalog()
    assert len(catalog.entries) >= 50


def test_catalog_integrity() -> None:
    catalog = load_catalog()
    slugs = [entry.slug for entry in catalog.entries]
    assert len(set(slugs)) == len(slugs)
    for entry in catalog.entries:
        assert normalize(entry.name)
        for alias in entry.aliases:
            assert normalize(alias) != normalize(entry.name), (entry.slug, alias)
        # Every entry resolves through its own slug (feature 13/14 invariant).
        assert catalog.lookup(entry.slug) is entry


def test_catalog_poll_labels() -> None:
    catalog = load_catalog()
    for label, slug in POLL_LABELS.items():
        entry = catalog.lookup(label)
        assert entry is not None, label
        assert entry.slug == slug, label
    salf = catalog.lookup("salf")
    alianca = catalog.lookup("alianca-cat")
    assert salf is not None and salf.name == "Se Acabó La Fiesta"
    assert alianca is not None and alianca.name == "Aliança Catalana"


def test_catalog_covers_2023_brands() -> None:
    brands = [
        line.strip()
        for line in (FIXTURES / "brands_2023.txt")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    assert len(brands) >= 50
    catalog = load_catalog()
    missing = [brand for brand in brands if catalog.lookup(brand) is None]
    assert missing == []


def test_catalog_punctuation_pairs() -> None:
    catalog = load_catalog()
    for dotted, clean in PUNCTUATION_PAIRS:
        dotted_entry = catalog.lookup(dotted)
        clean_entry = catalog.lookup(clean)
        assert dotted_entry is not None, dotted
        assert clean_entry is not None, clean
        assert dotted_entry.slug == clean_entry.slug, (dotted, clean)


def test_catalog_families_resolve() -> None:
    catalog = load_catalog()
    missing = [label for label in FAMILY_LABELS if catalog.lookup(label) is None]
    assert missing == []


def test_catalog_coalitions_do_not_merge() -> None:
    catalog = load_catalog()
    slugs = set()
    for label in ("Podemos", "Unidas Podemos", "Sumar"):
        entry = catalog.lookup(label)
        assert entry is not None, label
        slugs.add(entry.slug)
    assert len(slugs) == 3


# --- One shared slugify (R26) ------------------------------------------------


def test_slugify_single_source() -> None:
    from ingestor.elections.loaders import election
    from ingestor.polls.loaders import polls

    assert election.slugify is slugify
    assert polls.slugify is slugify
    assert slugify("C's") == "c-s"
    assert slugify("U.P.N.") == "u-p-n"
    assert slugify("  ") == ""
    assert slugify("Aliança Catalana") == "alianca-catalana"


# --- Resolution: catalogue -> existing name -> creation (R16-R25) -----------

# A catalogue with one ficha, so the resolver's fallbacks are exercised.
PP_CATALOG = """
[parties.pp]
name = "PP"
"""


def make_resolver(
    tmp_path: Path, catalog_text: str, parties: tuple[Party, ...] = ()
) -> PartyResolver:
    """Resolver over transient rows and a catalogue written under ``tmp_path``."""
    return PartyResolver(parties, load_catalog(write_catalog(tmp_path, catalog_text)))


def test_resolve_uses_catalog_slug(tmp_path: Path) -> None:
    text = """
[parties.bng]
name = "BNG"
"""
    party = make_resolver(tmp_path, text).resolve("B.N.G.")
    assert party.name == "BNG"
    assert party.slug == "bng"

    existing = Party(id=5, name="BNG", slug="bng")
    resolver = make_resolver(tmp_path, text, (existing,))
    assert resolver.resolve("B.N.G.") is existing


def test_resolve_catalog_creation_without_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    text = """
[parties.salf]
name = "Se Acabó La Fiesta"
"""
    resolver = make_resolver(tmp_path, text)
    with caplog.at_level(logging.WARNING):
        party = resolver.resolve("SALF")
    assert party.slug == "salf"
    assert party.name == "Se Acabó La Fiesta"
    assert caplog.records == []


def test_resolve_matches_existing_name(tmp_path: Path) -> None:
    existing = Party(id=3, name="B.N.G.", slug="b-n-g")
    resolver = make_resolver(tmp_path, PP_CATALOG, (existing,))
    assert resolver.resolve("BNG") is existing


def test_resolve_tie_break_slug_wins(tmp_path: Path) -> None:
    dotted = Party(id=3, name="B.N.G.", slug="b-n-g")
    clean = Party(id=7, name="BNG", slug="bng")
    resolver = make_resolver(tmp_path, PP_CATALOG, (dotted, clean))
    assert resolver.resolve("B.N.G.") is clean


def test_resolve_tie_break_lowest_id(tmp_path: Path) -> None:
    first = Party(id=9, name="U.P.L.", slug="u-p-l-x")
    second = Party(id=2, name="UPL", slug="upl-viejo")
    resolver = make_resolver(tmp_path, PP_CATALOG, (first, second))
    assert resolver.resolve("U.P.L.") is second


def test_resolve_creates_with_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    resolver = make_resolver(tmp_path, PP_CATALOG)
    label = "PARTIDO " + "X" * 80
    with caplog.at_level(logging.WARNING):
        party = resolver.resolve(label)
    assert party.name == label
    assert party.slug == slugify(label)[:60]
    assert "unknown party label" in caplog.text
    assert f"{label} -> {party.slug}" in caplog.text


def test_resolve_collision_suffix(tmp_path: Path) -> None:
    taken = Party(id=1, name="Otra marca", slug="fa")
    resolver = make_resolver(tmp_path, PP_CATALOG, (taken,))
    assert resolver.resolve("FA", code="01").slug == "fa-01"

    resolver = make_resolver(tmp_path, PP_CATALOG, (taken,))
    assert resolver.resolve("FA").slug == "fa-2"

    long_taken = Party(id=1, name="Otra marca", slug="a" * 60)
    resolver = make_resolver(tmp_path, PP_CATALOG, (long_taken,))
    party = resolver.resolve("A" * 60, code="01")
    assert len(party.slug) == 60
    assert party.slug.endswith("-01")


def test_resolve_is_idempotent(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    text = """
[parties.x]
name = "Equis"
aliases = ["Equis Brand"]
"""
    resolver = make_resolver(tmp_path, text)
    first = resolver.resolve("Equis")
    assert resolver.resolve("Equis") is first
    assert resolver.resolve("Equis Brand") is first

    with caplog.at_level(logging.WARNING):
        created = resolver.resolve("FA")
        assert resolver.resolve("FA") is created
    warnings = [r for r in caplog.records if "unknown party label" in r.getMessage()]
    assert len(warnings) == 1


def test_resolve_no_fuzzy_matching(tmp_path: Path) -> None:
    pp = Party(id=1, name="PP", slug="pp")
    resolver = make_resolver(tmp_path, PP_CATALOG, (pp,))
    party = resolver.resolve("PPX")
    assert party is not pp
    assert party.slug == "ppx"


# --- Contract: stdlib only, no new dependencies (R27) -----------------------


def test_module_has_no_new_dependencies() -> None:
    tree = ast.parse(Path(parties.__file__).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert "tomllib" in imported
    assert imported <= set(sys.stdlib_module_names) | {"ingestor"}

    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    project = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))["project"]
    dependencies = sorted(
        dependency.split(">=")[0].split("[")[0].strip().lower()
        for dependency in project["dependencies"]
    )
    assert dependencies == ["alembic", "psycopg", "pydantic-settings", "sqlalchemy"]
