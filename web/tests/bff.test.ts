import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

import * as latestElectionRoute from "../app/api/gold/latest-election/route.ts";
import * as nationalResultsRoute from "../app/api/gold/national-results/route.ts";
import { parseElectionId } from "../app/api/_lib/params.ts";

const root = fileURLToPath(new URL("..", import.meta.url));
const ROUTES = [
  "app/api/gold/latest-election/route.ts",
  "app/api/gold/national-results/route.ts",
];

function read(path: string): string {
  return readFileSync(join(root, path), "utf8");
}

// R2: electionId is a positive integer or a RangeError.
test("parseElectionId accepts positive integers and rejects everything else", () => {
  assert.equal(parseElectionId("1"), 1);
  assert.equal(parseElectionId("2023"), 2023);
  for (const raw of [null, "0", "-1", "abc", "", "1.5", " 1"]) {
    assert.throws(() => parseElectionId(raw), RangeError, `debe rechazar ${raw}`);
  }
});

// R2, R4: each route exports GET, opts out of static rendering and caching.
test("each Route Handler declares GET, force-dynamic and Cache-Control: no-store", () => {
  for (const path of ROUTES) {
    const source = read(path);
    assert.match(source, /export\s+(?:async\s+)?function\s+GET\b/, `${path}: falta GET`);
    assert.match(
      source,
      /export\s+const\s+dynamic\s*=\s*["']force-dynamic["']/,
      `${path}: falta force-dynamic`,
    );
    assert.match(source, /no-store/, `${path}: falta Cache-Control: no-store`);
    assert.doesNotMatch(source, /\b(?:SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)\b/);
    assert.doesNotMatch(source, /(?:from\s+["']pg["']|require\(\s*["']pg["']\s*\))/);
  }

  assert.equal(typeof latestElectionRoute.GET, "function");
  assert.equal(latestElectionRoute.dynamic, "force-dynamic");
  assert.equal(typeof nationalResultsRoute.GET, "function");
  assert.equal(nationalResultsRoute.dynamic, "force-dynamic");
});

// R4: bad input is a 400 without touching the database; errors keep the no-store contract.
test("national-results returns 400 for an invalid electionId without a database", async () => {
  for (const query of ["", "?electionId=0", "?electionId=-1", "?electionId=abc"]) {
    const response = await nationalResultsRoute.GET(
      new Request(`http://localhost/api/gold/national-results${query}`),
    );
    assert.equal(response.status, 400, `query ${query}`);
    assert.equal(response.headers.get("cache-control"), "no-store");
    const body = (await response.json()) as { error?: string };
    assert.equal(typeof body.error, "string");
  }
});
