import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

import {
  GOLD_SQL,
  SQL_LATEST_ELECTION,
  SQL_NATIONAL_RESULTS,
} from "../app/api/_lib/gold.ts";

const GOLD_DOC = readFileSync(
  fileURLToPath(new URL("../../docs/db/gold.md", import.meta.url)),
  "utf8",
);

function contractViews(): Set<string> {
  const views = new Set<string>();
  for (const line of GOLD_DOC.split("\n")) {
    const match = /^\| `([a-z_]+)` \|/.exec(line);
    if (match) views.add(match[1]);
  }
  return views;
}

const WRITE_SQL = /\b(insert|update|delete|create|alter|drop|truncate)\b/i;
const SELECTS = /\bselect\b/i;

function assertReadOnlyGoldSelect(sql: string, name: string): void {
  assert.doesNotMatch(sql, /;/, `${name}: una sola sentencia sin punto y coma`);
  assert.doesNotMatch(sql, WRITE_SQL, `${name}: solo SELECT de lectura`);
  assert.equal(
    sql.match(new RegExp(SELECTS, "gi"))?.length,
    1,
    `${name}: un único SELECT`,
  );

  const targets = [...sql.matchAll(/\b(?:from|join)\s+([a-z_][\w.]*)/gi)].map(
    (match) => match[1],
  );
  assert.ok(targets.length > 0, `${name}: consulta con FROM/JOIN`);
  const views = contractViews();
  for (const target of targets) {
    const [schema, view] = target.split(".");
    assert.equal(schema, "gold", `${name}: ${target} no apunta al esquema gold`);
    assert.ok(views.has(view), `${name}: ${view} no está en el contrato gold`);
  }
  assert.doesNotMatch(sql, /\b(silver|bronze)\./i, `${name}: nunca silver/bronze`);
}

// R2: every exported SQL is a single read-only SELECT over gold.* views.
test("every GOLD_SQL entry is a single read-only SELECT over contract views", () => {
  const entries = Object.entries(GOLD_SQL);
  assert.deepEqual(Object.keys(GOLD_SQL), ["latest_election", "national_results"]);
  for (const [name, sql] of entries) assertReadOnlyGoldSelect(sql, name);
  assert.equal(GOLD_SQL.latest_election, SQL_LATEST_ELECTION);
  assert.equal(GOLD_SQL.national_results, SQL_NATIONAL_RESULTS);
});

// R2: the latest election is the one with the highest election_date.
test("latest election query orders by election_date desc and limits to one", () => {
  assert.match(SQL_LATEST_ELECTION, /\bfrom\s+gold\.election_summary\b/i);
  assert.match(SQL_LATEST_ELECTION, /\border\s+by\s+election_date\s+desc\b/i);
  assert.match(SQL_LATEST_ELECTION, /\blimit\s+1\b/i);
});

// R2: national results are filtered by election id and the closed level vocabulary.
test("national results query filters by $1 and level = 'national'", () => {
  assert.match(SQL_NATIONAL_RESULTS, /\bfrom\s+gold\.result_by_area\b/i);
  assert.match(SQL_NATIONAL_RESULTS, /\bwhere\s+election_id\s*=\s*\$1\b/i);
  assert.match(SQL_NATIONAL_RESULTS, /\blevel\s*=\s*'national'/i);
});
