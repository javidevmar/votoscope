"""Adapter for Congreso (Congress) elections, process code 02.

All Congress processes 1986-2023 share the same record layouts; the
year-specific peculiarities found in the source files are handled here.
"""

from __future__ import annotations

import logging
from pathlib import Path

from ingestor.elections.parsers.common import StationRef

logger = logging.getLogger(__name__)

# The ministry's own files 09 and 10 disagree on the per-station
# "votos a candidaturas" total in these processes (see
# .agents/data-sources.md): the check is downgraded to a warning there
# instead of failing the load.
RELAXED_STATION_TOTALS = {1986, 1989, 1993, 1996, 2000, 2004, 2015}


class CongresoAdapter:
    """Rules of the Congress process."""

    process_code = "02"
    election_type = "congress"
    source = "infoelectoral"

    # File kinds read by the loader; 05 is optional (name source only).
    file_kinds = ("02", "03", "05", "09", "10")
    required_file_kinds = ("02", "03", "09", "10")

    def find_files(self, directory: Path) -> dict[str, Path]:
        """Return the source files of one election directory, by file kind."""
        files: dict[str, Path] = {}
        for kind in self.file_kinds:
            matches = sorted(directory.glob(f"{kind}{self.process_code}*.DAT"))
            if len(matches) > 1:
                raise ValueError(f"more than one {kind} file in {directory}: {matches}")
            if matches:
                files[kind] = matches[0]
        return files

    def normalize_candidacy_code(self, code: str, known_codes: set[str]) -> str:
        """Fix the 2015 CERA quirk: file 10 uses ``9xxxxx`` for candidacies
        published in file 03 as ``0xxxxx``. Only codes absent from 03 and
        whose ``9``-to-``0`` rewrite exists are rewritten.
        """
        if code in known_codes:
            return code
        if code.startswith("9") and "0" + code[1:] in known_codes:
            return "0" + code[1:]
        return code

    def skip_aggregate(self, row: StationRef) -> bool:
        """Skip CERA totals above the province level (sums, not facts)."""
        return row.province_code == "99"

    def strict_station_totals(self, year: int) -> bool:
        """Whether the 09 vs 10 per-station total check must fail the load."""
        return year not in RELAXED_STATION_TOTALS
