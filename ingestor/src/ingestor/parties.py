"""Party identity: label normalization, curated catalogue and resolution.

The catalogue (``data/party_catalog.toml``) is curated in the repository: each
``[parties.<slug>]`` table carries the literal ``name`` and the ``aliases``
(spellings that do not coincide after normalization).
"""

from __future__ import annotations

import logging
import re
import tomllib
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from ingestor.errors import IngestError
from ingestor.models import Party

logger = logging.getLogger(__name__)

CATALOG_PATH: Path = Path(__file__).parent / "data" / "party_catalog.toml"
SLUG_MAX = 60  # silver.party.slug is String(60)


def normalize(label: str) -> str:
    """Normalized label key: NFKD-folded, diacritics stripped, alphanumeric upper."""
    folded = unicodedata.normalize("NFKD", label)
    return "".join(
        char for char in folded if char.isalnum() and not unicodedata.combining(char)
    ).upper()


def slugify(value: str) -> str:
    """ASCII, lowercase, dash-separated slug (for party slugs)."""
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


@dataclass(frozen=True)
class PartyEntry:
    """One curated electoral brand: canonical slug, literal name and aliases."""

    slug: str
    name: str
    aliases: tuple[str, ...] = ()


class Catalog:
    """Curated brands, indexed by the normalized keys of name, slug and aliases."""

    def __init__(self, entries: Iterable[PartyEntry]) -> None:
        self.entries = tuple(entries)
        self._by_key: dict[str, PartyEntry] = {}
        for entry in self.entries:
            keys = (normalize(entry.name), normalize(entry.slug))
            keys += tuple(normalize(alias) for alias in entry.aliases)
            for key in keys:
                self._by_key[key] = entry

    def lookup(self, label: str) -> PartyEntry | None:
        """Entry whose name, slug or alias normalizes like ``label``, if any."""
        return self._by_key.get(normalize(label))


def load_catalog(path: Path = CATALOG_PATH) -> Catalog:
    """Read and validate the catalogue TOML: unique keys and meaningful aliases."""
    try:
        with path.open("rb") as handle:
            document = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise IngestError(
            f"{path}: cannot read the party catalogue: {error}"
        ) from error

    table = document.get("parties")
    if not isinstance(table, dict):
        raise IngestError(f"{path}: missing the [parties] table")

    entries: list[PartyEntry] = []
    owners: dict[str, str] = {}

    def claim(key: str, slug: str) -> None:
        owner = owners.setdefault(key, slug)
        if owner != slug:
            raise IngestError(
                f"{path}: party key {key!r} is claimed by both {owner!r} and {slug!r}"
            )

    for slug, ficha in table.items():
        if not isinstance(ficha, dict) or not isinstance(ficha.get("name"), str):
            raise IngestError(f"{path}: party {slug!r} declares no name")
        name = ficha["name"]
        aliases = ficha.get("aliases", [])
        if not isinstance(aliases, list) or not all(
            isinstance(alias, str) for alias in aliases
        ):
            raise IngestError(f"{path}: party {slug!r}: aliases must be a string list")
        name_key = normalize(name)
        for value in (name, *aliases):
            if not normalize(value):
                raise IngestError(
                    f"{path}: party {slug!r}: {value!r} has no alphanumeric characters"
                )
        claim(name_key, slug)
        for alias in aliases:
            key = normalize(alias)
            if key == name_key:
                raise IngestError(
                    f"{path}: party {slug!r}: alias {alias!r} is redundant with its name"
                )
            claim(key, slug)
        claim(normalize(slug), slug)
        entries.append(PartyEntry(slug=slug, name=name, aliases=tuple(aliases)))

    return Catalog(entries)


class PartyResolver:
    """Resolve labels to ``silver.party`` rows: catalogue → existing name → creation."""

    def __init__(self, parties: Iterable[Party], catalog: Catalog) -> None:
        self.catalog = catalog
        self.by_slug: dict[str, Party] = {}
        self.by_name: dict[str, list[Party]] = {}
        for party in parties:
            self._index(party)

    def resolve(self, label: str, *, code: str | None = None) -> Party:
        """Row for ``label``: its catalogue ficha, an existing homonym, or a new row.

        New rows are not added to a session: the caller does ``session.add`` and
        flushes. Created rows are indexed, so resolving the same label twice
        returns one row.
        """
        entry = self.catalog.lookup(label)
        if entry is not None:
            party = self.by_slug.get(entry.slug)
            if party is None:
                party = Party(name=entry.name, slug=entry.slug)
                self._index(party)
            return party

        key = normalize(label)
        matches = self.by_name.get(key)
        if matches:
            return self._prefer(matches, key)

        slug = self._free_slug(slugify(label) or "party", code)
        logger.warning("unknown party label: %s -> %s", label, slug)
        party = Party(name=label, slug=slug)
        self._index(party)
        return party

    def _index(self, party: Party) -> None:
        self.by_slug[party.slug] = party
        self.by_name.setdefault(normalize(party.name), []).append(party)

    def _prefer(self, matches: list[Party], key: str) -> Party:
        """The row whose slug is the canonical one, else the one with the lowest id."""
        canonical = slugify(key)
        for party in matches:
            if party.slug == canonical:
                return party
        return min(matches, key=lambda party: party.id)

    def _free_slug(self, base: str, code: str | None) -> str:
        """First free variant of ``base``: itself, ``-<code>`` or ``-2``, ``-3``..."""
        base = base[:SLUG_MAX]
        if base not in self.by_slug:
            return base
        if code is not None:
            candidate = _with_suffix(base, f"-{code}")
            if candidate not in self.by_slug:
                return candidate
        number = 2
        while (candidate := _with_suffix(base, f"-{number}")) in self.by_slug:
            number += 1
        return candidate


def _with_suffix(base: str, suffix: str) -> str:
    """``base`` trimmed so that ``base + suffix`` fits in ``party.slug``."""
    return base[: SLUG_MAX - len(suffix)] + suffix
