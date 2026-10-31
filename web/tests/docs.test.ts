import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

function read(relative: string): string {
  return readFileSync(fileURLToPath(new URL(`../../${relative}`, import.meta.url)), "utf8");
}

function assertContains(source: string, values: string[], document: string): void {
  for (const value of values) {
    assert.ok(source.includes(value), `${document} debe mencionar ${value}`);
  }
}

// R15: the frontend constitution documents the scaffold, BFF, role, logging and tests.
test("web/AGENTS.md documents the scaffold, BFF, role, logging and tests", () => {
  const agents = read("web/AGENTS.md");
  assertContains(
    agents,
    [
      "votoscope_web",
      "app/api/",
      "pnpm test",
      "node --test",
      "LOG_LEVEL",
      "ALTER ROLE",
      "docs/db/gold.md",
    ],
    "web/AGENTS.md",
  );
});

// R16: conventions fixes the web test strategy, BFF rule, logging and pnpm.
test(".agents/conventions.md includes the web strategy", () => {
  const conventions = read(".agents/conventions.md");
  assertContains(
    conventions,
    ["node --test", "web/tests", "pnpm", "app/api/", "LOG_LEVEL"],
    ".agents/conventions.md",
  );
  assert.doesNotMatch(conventions, /se decidirá en su scaffold/i);
});

// R17: architecture and environment describe the scaffold as done.
test("architecture and environment no longer call the web pending", () => {
  const architecture = read(".agents/architecture.md");
  const environment = read(".agents/environment.md");

  for (const [document, source] of [
    [".agents/architecture.md", architecture],
    [".agents/environment.md", environment],
  ] as const) {
    assert.doesNotMatch(source, /pendiente de scaffold/i, `${document} sigue pendiente`);
    assertContains(source, ["web/", "pnpm dev", "votoscope_web"], document);
  }
  assertContains(environment, [".env.local"], ".agents/environment.md");
});

// R19: the frontend README is the human quickstart.
test("web/README.md is the quickstart guide", () => {
  const readme = read("web/README.md");
  assertContains(
    readme,
    [
      "Node",
      "24",
      "pnpm",
      "pnpm dev",
      ".env.local",
      "votoscope_web",
      "app/api/",
      "shadcn",
      "docs/db/gold.md",
    ],
    "web/README.md",
  );
});
