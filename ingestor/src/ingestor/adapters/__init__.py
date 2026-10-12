"""Adapter registry: process code -> adapter.

One module per election process; new processes add a module and a registry
entry, without touching the parsers or the loader.
"""

from __future__ import annotations

from pathlib import Path

from ingestor.adapters.congreso import CongresoAdapter
from ingestor.errors import IngestError
from ingestor.parsers.common import read_records

_ADAPTERS: dict[str, CongresoAdapter] = {
    CongresoAdapter.process_code: CongresoAdapter(),
}


def adapter_for_process(process_code: str) -> CongresoAdapter:
    try:
        return _ADAPTERS[process_code]
    except KeyError:
        raise IngestError(f"no adapter for process code {process_code!r}") from None


def adapter_for_directory(directory: Path) -> CongresoAdapter:
    """Identify the adapter from the process code in the 02 file."""
    matches = sorted(directory.glob("02*.DAT"))
    if not matches:
        raise IngestError(f"no identification file (02*.DAT) in {directory}")
    record = next(read_records(matches[0]), None)
    if not record:
        raise IngestError(f"empty identification file: {matches[0]}")
    return adapter_for_process(record[0:2])
