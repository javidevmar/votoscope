import assert from "node:assert/strict";
import { after, test } from "node:test";

import { getPool, queryRows } from "../app/api/_lib/db.ts";
import {
  getLatestElection,
  getNationalResults,
} from "../app/api/_lib/gold.ts";

const UNAVAILABLE =
  /ECONNREFUSED|ENOTFOUND|ETIMEDOUT|does not exist|password authentication|connect/i;

after(async () => {
  if (process.env.DATABASE_URL) await getPool().end();
});

function skipIfUnavailable(t: { skip: (reason?: string) => void }, error: unknown): void {
  const message = error instanceof Error ? error.message : String(error);
  if (UNAVAILABLE.test(message)) {
    t.skip(`Postgres no disponible: ${message}`);
    return;
  }
  throw error;
}

// R2, R3: the service reads the latest election and its national results.
test("latest election matches max(election_date) and national results are typed", async (t) => {
  if (!process.env.DATABASE_URL) {
    t.skip("DATABASE_URL no está definida");
    return;
  }

  let election;
  try {
    election = await getLatestElection();
  } catch (error) {
    skipIfUnavailable(t, error);
    return;
  }

  if (!election) {
    t.skip("gold.election_summary está vacía");
    return;
  }

  const [latest] = await queryRows<{ max_date: string }>(
    "SELECT max(election_date)::text AS max_date FROM gold.election_summary",
  );
  const localDate = [
    election.electionDate.getFullYear(),
    String(election.electionDate.getMonth() + 1).padStart(2, "0"),
    String(election.electionDate.getDate()).padStart(2, "0"),
  ].join("-");
  assert.equal(
    localDate,
    latest.max_date,
    "la última elección es la de election_date máxima",
  );

  assert.equal(typeof election.electionId, "number");
  assert.equal(typeof election.electionType, "string");
  assert.ok(election.electionName === null || typeof election.electionName === "string");
  for (const value of [
    election.census,
    election.nullVotes,
    election.blankVotes,
    election.candidatureVotes,
    election.validVotes,
    election.voters,
  ]) {
    assert.equal(typeof value, "number");
    assert.ok(Number.isFinite(value));
  }
  assert.ok(
    election.turnoutPct === null ||
      (typeof election.turnoutPct === "number" && Number.isFinite(election.turnoutPct)),
  );

  const results = await getNationalResults(election.electionId);
  assert.ok(results.length > 0, "hay resultados nacionales");
  for (let index = 0; index < results.length; index += 1) {
    const result = results[index];
    assert.equal(typeof result.partyId, "number");
    assert.equal(typeof result.partySlug, "string");
    assert.equal(typeof result.partyName, "string");
    assert.ok(result.partyColor === null || typeof result.partyColor === "string");
    assert.equal(typeof result.votes, "number");
    assert.ok(result.pct === null || (result.pct >= 0 && result.pct <= 100));
    if (index > 0) {
      assert.ok(
        results[index - 1].votes >= result.votes,
        "los resultados llegan ordenados por votos descendentes",
      );
    }
  }
});

// R13: debug logging during a real query never leaks the connection or credentials.
test("debug logs never contain the connection URL or password", async (t) => {
  const url = process.env.DATABASE_URL;
  if (!url) {
    t.skip("DATABASE_URL no está definida");
    return;
  }

  const originalLevel = process.env.LOG_LEVEL;
  const originalConsole = { log: console.log, warn: console.warn, error: console.error };
  const lines: string[] = [];
  process.env.LOG_LEVEL = "debug";
  console.log = (line: string) => lines.push(line);
  console.warn = (line: string) => lines.push(line);
  console.error = (line: string) => lines.push(line);

  try {
    await getLatestElection();
  } catch (error) {
    skipIfUnavailable(t, error);
    return;
  } finally {
    console.log = originalConsole.log;
    console.warn = originalConsole.warn;
    console.error = originalConsole.error;
    if (originalLevel === undefined) delete process.env.LOG_LEVEL;
    else process.env.LOG_LEVEL = originalLevel;
  }

  assert.ok(lines.length > 0, "LOG_LEVEL=debug registra la consulta");
  const output = lines.join("\n");
  assert.ok(!output.includes(url), "los logs no incluyen DATABASE_URL");
  const password = new URL(url).password;
  if (password) assert.ok(!output.includes(password), "los logs no incluyen la contraseña");
});
