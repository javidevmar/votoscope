# Tareas — `party_catalog`

TDD en parejas tests → código; cada task es un commit atómico. Sin cambios de modelo (ERD ↔ `models.py` ↔ migración no aplican). Sin CLI. Detalle en [`design.md`](design.md) y requisitos en [`requirements.md`](requirements.md).

- [ ] T1 — Extraer de `silver` local (SQL de `design.md` §Curación; los 13 procesos) y crear `ingestor/tests/fixtures/party_catalog/brands_2023.txt` con los `name` del proceso del 23-jul-2023, uno por línea y literales. Cubre: R12, R28.
- [ ] T2 — Tests en rojo de `normalize`: matriz con mayúsculas, NFKD y diacríticos (`ç`, `ñ`, tildes), puntuación (`.`, `'`, `-`, `,`), espacios y claves sin alfanumérico. Cubre: R1.
- [ ] T3 — Implementar `normalize` en `ingestor/src/ingestor/parties.py`. En verde para T2. Cubre: R1.
- [ ] T4 — Tests en rojo de catálogo: `load_catalog`/`lookup` con TOML de `tmp_path` (nombre, alias, alias por normalización, `None` si no está) y los errores de integridad (clave duplicada entre fichas, alias redundante, clave sin alfanumérico, fichero inexistente o TOML inválido, ficha sin `name`). Cubre: R2, R3, R4, R5, R6, R7, R8, R9.
- [ ] T5 — Implementar `PartyEntry`, `Catalog` y `load_catalog`. En verde para T4. Cubre: R2, R3, R4, R5, R6, R7, R8, R9.
- [ ] T6 — Tests en rojo del catálogo real: carga por la ruta por defecto e integridad; las 15 etiquetas de sondeos → slugs y nombres de `salf`/`alianca-cat`; pares punteados; familias del diagnóstico; coaliciones sin fusionar; fixture del 2023 (todas las líneas resuelven). Cubre: R2, R5, R6, R10, R11, R12, R13, R14, R15, R28.
- [ ] T7 — Redactar `ingestor/src/ingestor/data/party_catalog.toml` desde la extracción de T1 (fichas del alcance, literales; decisiones de familia registradas en el diff). En verde para T6. Cubre: R10, R11, R12, R13, R14, R15.
- [ ] T8 — Tests en rojo de `slugify` compartida: identidad en los tres módulos (`parties`, `election`, `polls`) y casos (`C's`→`c-s`, `U.P.N.`→`u-p-n`, vacío). Cubre: R26.
- [ ] T9 — Mover `slugify` a `parties.py` y actualizar los imports de `elections/loaders/election.py` y `polls/loaders/polls.py` (sin definiciones locales). En verde para T8. Cubre: R26.
- [ ] T10 — Tests en rojo del resolver: precedencia catálogo → nombre → alta; creación por ficha sin warning; desempates (slug canónico e `id` menor); alta con warning `unknown party label`, nombre literal y slug recortado; colisiones (`-code` y `-2`); sin fuzzy (`PPX`); idempotencia de la instancia. Cubre: R16, R17, R18, R19, R20, R21, R22, R23, R24, R25.
- [ ] T11 — Implementar `PartyResolver`. En verde para T10. Cubre: R16, R17, R18, R19, R20, R21, R22, R23, R24, R25.
- [ ] T12 — Tests de contrato: imports del módulo solo de stdlib e `ingestor` (incluido `tomllib`), y `ingestor/pyproject.toml` sin dependencias nuevas. Cubre: R27.
- [ ] T13 — Puerta final: `./init.sh` en verde (ruff, format, pytest, `alembic check`) y escribir `progress/impl_party_catalog.md` con la trazabilidad R1–R28 ↔ tests y la extracción usada (SQL + salida). Cubre: R1–R28.
