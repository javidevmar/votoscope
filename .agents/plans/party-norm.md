# Identidad canónica de partidos (normalización y deduplicación)

Estado: abierto · Creado: 2026-10-12 · Abierto: 2026-10-12
Objetivo: unificar la identidad de partido entre las generales del Congreso y los sondeos de Wikipedia —catálogo compartido + resolución por nombre normalizado— y recalcular `silver`.

## Diagnóstico (local, 2026-10-12)

- `silver.party` tiene **547 filas** para 13 procesos (387 de un solo proceso, 160 en varios). La identidad se deriva de las siglas de la cabecera nacional del `03` (`_resolve_parties`, slug de las siglas): la misma marca con otra grafía en otro año crea fila nueva.
- **27 grupos** de filas con el mismo nombre salvo puntuación: `B.N.G.`/`BNG`, `P.P.`/`PP`, `P.S.O.E.`/`PSOE`, `C's`/`Cs`, `I.U.`/`IU`, `P.C.P.E.`/`PCPE`, `U.P.L.`/`UPL`, `F.I.A.`/`FIA`, `D.N.`/`DN`, `A.u.N.`/`AUN`… (55 filas en total). No es solo histórico: en el 2023 del MVP (59 filas de `party`), BNG, UPL y FIA están en la fila punteada —el BNG alterna (limpia en 1986–2004, 2011 y 2019; punteada en 2008 y 2023), UPL va limpio en 1993–2019 y punteado en 2023, y FIA limpio en 2019 y punteado en 2023—: la web partiría las series justo en el año que enseña.
- Grafías **distintas** que ya son curación, no puntuación: familia Podemos (`podemos`, `podemos-iu-…`, `unidas podemos`), verdes (`lv`, `lve`, `lv-gv`, `verdes`), `fe-de-las-j`/`fe-de-las-jons`/`fe-jons`, `na`/`na-bai`, `erc`/`esquerra`/`erc-catsi`…
- **Sondeos**: 13 de las 15 etiquetas del [plan de sondeos](polls-wikipedia.md) ya resuelven a slugs existentes (`pp`, `psoe`, `vox`, `sumar`, `erc`, `jxcat-junts`, `eh-bildu`, `eaj-pnv`, `bng`, `cca`, `u-p-n`, `adelante-andalucia`, `podemos`); `salf` y `alianca-cat` se crearían al primer snapshot y el `03` de 2026 crearía filas por su cuenta (`se-acabo-la-fiesta`…). Sin una identidad común, la web no puede unir sondeos y resultados por partido. `poll`/`poll_result` aún no existen: el catálogo llega antes que ese adaptador.

## Decisión

- **Catálogo versionado en el paquete**: `ingestor/src/ingestor/data/party_catalog.toml` — por slug canónico, `name` (siglas legibles, como hasta ahora) y `aliases` (grafías que no coincidan por normalización). Es curación, no descarga, así que va en git (a diferencia de `refs/`); TOML leído con `tomllib` de la stdlib: sin dependencias nuevas.
- **Resolución compartida** en `src/ingestor/parties.py`, usada por el loader de elecciones y, cuando nazca, el de sondeos. Para una etiqueta (siglas de cabecera del `03`, columna de la wiki):
  1. clave = etiqueta normalizada (NFKD, mayúsculas, fuera todo lo no alfanumérico: `B.N.G.`→`BNG`, `C's`→`CS`, `P. RIOJANO`→`PRIOJANO`);
  2. alias del catálogo → slug canónico;
  3. coincidencia con el nombre normalizado de un `party` existente (desempate: el slug igual a `slugify(clave)`; si no, el `id` menor);
  4. nada: alta como hasta hoy (`slugify` de las siglas, código de cabecera como sufijo si colisiona) + warning — el aviso es la señal de añadir ficha.
- **Sin cambio de esquema**: `party` y `party_election` valen tal cual; ERD, modelos y migración quietos. `silver` se recalcula reingiriendo (contrato bronce→plata); ningún fichero fuente se toca.
- **Criterio de identidad**: continuidad de la **marca electoral**. Grafías de la misma marca se fusionan; coaliciones con nombre propio no (`Podemos` ≠ `Unidas Podemos` ≠ `Sumar`, aunque compartan cartel) — si el frente quiere una línea continua, se agrupa en `gold`.
- **Alcance de la curación inicial**: las 15 etiquetas de sondeos, las marcas del 2023 (59 filas) y las familias del diagnóstico. Los micro-partidos de un solo proceso caen por la vía normal (paso 3) sin ficha. `party.color` (hoy nulo en las 547) sigue fuera: se curará con `gold`, como dice el plan de sondeos.
- Al terminar la recarga, los `party` sin candidaturas se borran con el `DELETE` de mantenimiento de abajo; no es DDL de esquema.

## Tareas

Cada una, un commit atómico; TDD donde toca (los tests fijan grafías y desenlaces, incluido el warning del alta).

1. **Catálogo + resolución** — `data/party_catalog.toml`, `parties.py` y tests: normalización, precedencia (catálogo → nombre existente → alta), desempates y altas con warning; integridad del catálogo (slugs y claves de alias únicos; las 15 etiquetas de sondeos cubiertas).
2. **Loader de elecciones** — `_resolve_parties` pasa por `parties.py`; test con dos procesos de siglas punteadas → un solo `party`; actualizar [`../data-model.md`](../data-model.md) (la identidad deja de ser provisional), [`../../docs/ingestor/ingesta.md`](../../docs/ingestor/ingesta.md) y [`../../ingestor/AGENTS.md`](../../ingestor/AGENTS.md) si su descripción deja de cuadrar.
3. **Recarga y verificación** — `ingest --force` de los 13 procesos; comprobaciones de abajo; borrar huérfanos.
4. **Sondeos** — el adaptador resuelve sus columnas contra el mismo catálogo y sustituye su tabla de mapeo (editar `polls-wikipedia.md` en la misma tarea). Test de que `poll_result.party_id` y `party_election.party_id` de la misma marca coinciden. El trabajo vive en ese plan.
5. **Cierre** — plegar lo durable a los docs, [`status.md`](../status.md) y plan a `hecho`.

## Comprobación (tras la recarga)

Sin grupos repetidos por puntuación (0 filas):

```sql
SELECT array_agg(slug) AS slugs, count(*)
FROM silver.party
GROUP BY upper(regexp_replace(name, '[^a-zA-Z0-9]', '', 'g'))
HAVING count(*) > 1;
```

BNG, UPL, FIA, Cs, PP, PSOE e IU en una única fila cada uno:

```sql
SELECT p.slug, p.name, count(DISTINCT pe.election_id) AS procesos
FROM silver.party p JOIN silver.party_election pe ON pe.party_id = p.id
WHERE upper(regexp_replace(p.name, '[^a-zA-Z0-9]', '', 'g'))
      IN ('BNG','UPL','FIA','CS','PP','PSOE','IU')
GROUP BY p.id ORDER BY p.slug;
```

Huérfanos (tras la recarga completa; cuando existan sondeos, excluir también `poll_result`):

```sql
DELETE FROM silver.party p
WHERE NOT EXISTS (SELECT 1 FROM silver.party_election pe WHERE pe.party_id = p.id);
```

Los hechos no cambian: `vote`, `turnout` y `party_election` siguen igual salvo el `party_id` de las candidaturas fusionadas.

## Flecos y riesgos

- **Qué es la misma marca** en casos límite (coaliciones, verdes, falange) es juicio de curación: el catálogo lo deja escrito y revisable en el diff; el criterio ya está fijado arriba.
- **Los slugs de las filas fusionadas cambian** (p. ej. desaparece el punteado): hoy nadie los consume (ni `gold` ni la web), y hacerlo antes de la Entrega es precisamente el momento barato.
- **2026**: el catálogo debe tener ficha de SALF, Aliança.cat y las marcas de la nueva general antes de ingerir su `03`; aun así, el loader avisa de cualquier alta.
- **Otros procesos** (Senado, autonómicas): comparten catálogo y resolución sin nada extra; el mismo resolver sirve.
- Si algún día la curación deja de ser de repo (UI sobre la BD), el catálogo se muda a tabla; hoy no hace falta.
