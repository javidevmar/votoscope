# Tareas — `polls_adapter`

TDD: cada pareja tests → código va en dos tasks consecutivas; cada task es un commit atómico. Sin cambios de modelo (ERD ↔ `models.py` ↔ migración no aplican). Detalle en [`design.md`](design.md).

- [ ] T1 — Obtener el snapshot (`uv run ingestor fetch-polls` si no hay ninguno en `data/raw/polls/`) y crear las seis fixtures en `ingestor/tests/fixtures/wikipedia_polls/`: recortes literales `real_2026_head.wikitext` y `real_2023_tail.wikitext` (límites en `design.md`) + sintéticas `synthetic_dates.wikitext`, `synthetic_cells.wikitext`, `synthetic_columns.wikitext` y `synthetic_out_of_scope.wikitext`. Cubre: R28.
- [ ] T2 — Tests en rojo del alcance: `poll_tables` devuelve (año, tabla) solo de la sección `Voting intention estimates` y sus subsecciones por año (fixture real + señuelo ignorado) y, sin la sección, warning `section not found` + lista vacía (cadena inline). Cubre: R2, R25.
- [ ] T3 — Implementar en `ingestor/src/ingestor/polls/adapters/wikipedia_polls.py` `_split_sections` (corte jerárquico) y `poll_tables`. En verde para T2. Cubre: R2, R25.
- [ ] T4 — Tests en rojo del plan de columnas: fijas por rótulo (orden cambiado), columnas de partido por rótulo de wikilink (alt, `link=`, plano, Adelante Andalucía), `PARTY_COLUMNS` (15 slugs únicos + nombres de SALF/Aliança.cat), `ELECTION_TYPE`, cabecera de colores ignorada (recorte real sin warnings de columna), `FA` desconocida → warning + ignorada, `Lead` sin warning. Cubre: R3, R4, R5, R6, R7, R8, R9, R26.
- [ ] T5 — Implementar `_label`, `PARTY_COLUMNS`, `_column_plan` (con los warnings de columna desconocida y el guard de rótulos fijos) y `ELECTION_TYPE`; `parse_polls` lee la firma con el plan. En verde para T4. Cubre: R3–R9, R26.
- [ ] T6 — Tests en rojo de filas y resultados: separadoras y fila `#EFEFEF` saltadas (recorte de 2023), celdas de partido (`–`, `?`, `<2.0`, rango `135/137`, nota sola, `<br />`, solo pct, `?`+escaños), una fila por fila de datos con `source` literal (CIS), contrato de `PollRow`/`PollResultRow`. Cubre: R1, R10, R11, R12, R13, R14, R20.
- [ ] T7 — Implementar el bucle de filas (saltos, `_parse_party_cell`, emisión de resultados con valor, `source`). En verde para T6. Cubre: R1, R10–R14, R20.
- [ ] T8 — Tests en rojo de fechas: matriz de `parse_date` (`5 Oct`, `10–11 Oct`, `29 Sep–1 Oct`, `29 Dec–5 Jan`, `31 Dec–3 Jan`, `?`, basura → warning + nulas) + fixture sintética (cruce → año−1; día único → inicio=fin) + bloque del CIS con fecha compartida por `rowspan`. Cubre: R15, R16, R17, R22 (fecha).
- [ ] T9 — Implementar `parse_date` y conectarla a la lectura de filas. En verde para T8. Cubre: R15, R16, R17.
- [ ] T10 — Tests en rojo de muestra y participación: `1,000` → 1000, `?` → nulo; `67.6`/`66` → Decimal, `?` → nulo (fixtures sintética y real). Cubre: R18, R19.
- [ ] T11 — Implementar `_parse_sample` y `_parse_turnout`. En verde para T10. Cubre: R18, R19.
- [ ] T12 — Tests en rojo de firma y reestimaciones: `_pollster_name` (`SocioMétrica/El Español`, `CIS (Target Point)`, `More in Common`) y el bloque del CIS del recorte real (tres filas, fuentes literales). Cubre: R20, R21.
- [ ] T13 — Implementar `_pollster_name`. En verde para T12. Cubre: R21.
- [ ] T14 — Tests en rojo de robustez: celdas basura → warning + nulo; fila con celdas de menos → warning `column count mismatch` + saltada; tabla sin los cuatro rótulos fijos → warning `not a polls table` + saltada (cadenas inline). Cubre: R22, R23, R24.
- [ ] T15 — Implementar los warnings de robustez y los guards. En verde para T14. Cubre: R22, R23, R24.
- [ ] T16 — Tests de contrato, pureza, fixtures y docs: `ELECTION_TYPE`; módulo sin imports fuera de la stdlib ni de `polls/parsers/wikitext` y sin `urlopen`/`socket`/`requests`/`httpx`/`open(`/`sqlalchemy`/`SessionLocal`; las seis fixtures presentes; subcadenas `wikipedia_polls.py` y `sondeos` en `ingestor/AGENTS.md`. Cubre: R26, R27, R28, R29.
- [ ] T17 — Actualizar el bullet de `src/ingestor/polls/` en `ingestor/AGENTS.md`. En verde para T16. Cubre: R29.
- [ ] T18 — Puerta final: `./init.sh` en verde (ruff, pytest, `alembic check`) y escribir `progress/impl_polls_adapter.md` con la tabla de trazabilidad R1–R29 ↔ tests. Cubre: R1–R29.
