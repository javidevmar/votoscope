import assert from "node:assert/strict";
import { afterEach, beforeEach, test } from "node:test";

import { createLogger, parseLogLevel } from "../lib/logging.ts";

type Entry = { channel: "log" | "warn" | "error"; line: string };

function capture(): { sink: { log: (line: string) => void; warn: (line: string) => void; error: (line: string) => void }; entries: Entry[] } {
  const entries: Entry[] = [];
  return {
    entries,
    sink: {
      log: (line) => entries.push({ channel: "log", line }),
      warn: (line) => entries.push({ channel: "warn", line }),
      error: (line) => entries.push({ channel: "error", line }),
    },
  };
}

const originalLevel = process.env.LOG_LEVEL;

beforeEach(() => {
  delete process.env.LOG_LEVEL;
});

afterEach(() => {
  if (originalLevel === undefined) delete process.env.LOG_LEVEL;
  else process.env.LOG_LEVEL = originalLevel;
});

// R10: niveles y formato propio sobre console.
test("format: ISO timestamp, level and scope", () => {
  const { sink, entries } = capture();
  process.env.LOG_LEVEL = "debug";

  createLogger(sink).info("hola");

  assert.equal(entries.length, 1);
  assert.equal(entries[0].channel, "log");
  assert.match(
    entries[0].line,
    /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z info {2}\[votoscope-web\] hola$/,
  );
});

// R10: debug/info -> console.log, warn -> console.warn, error -> console.error.
test("channels: debug/info go to log, warn to warn, error to error", () => {
  const { sink, entries } = capture();
  process.env.LOG_LEVEL = "debug";

  const logger = createLogger(sink);
  logger.debug("d");
  logger.info("i");
  logger.warn("w");
  logger.error("e");

  assert.deepEqual(
    entries.map((entry) => entry.channel),
    ["log", "log", "warn", "error"],
  );
});

// R11: solo se escribe si el nivel es igual o superior al efectivo.
test("filtering: LOG_LEVEL=warn drops debug and info", () => {
  const { sink, entries } = capture();
  process.env.LOG_LEVEL = "warn";

  const logger = createLogger(sink);
  logger.debug("d");
  logger.info("i");
  logger.warn("w");
  logger.error("e");

  assert.deepEqual(
    entries.map((entry) => entry.line.split(" ")[1]),
    ["warn", "error"],
  );
});

test("filtering: LOG_LEVEL=error drops everything below error", () => {
  const { sink, entries } = capture();
  process.env.LOG_LEVEL = "error";

  const logger = createLogger(sink);
  logger.debug("d");
  logger.info("i");
  logger.warn("w");

  assert.equal(entries.length, 0);
});

// R12: sin variable o con valor inválido, el nivel efectivo es info.
test("fallback: undefined and unknown values mean info", () => {
  assert.equal(parseLogLevel(undefined), "info");
  assert.equal(parseLogLevel("verbose"), "info");
  assert.equal(parseLogLevel(""), "info");
  assert.equal(parseLogLevel("DEBUG"), "debug");
  assert.equal(parseLogLevel("Warn"), "warn");
});

test("fallback: without LOG_LEVEL debug is dropped and info is written", () => {
  const { sink, entries } = capture();

  const logger = createLogger(sink);
  logger.debug("d");
  logger.info("i");

  assert.equal(entries.length, 1);
  assert.match(entries[0].line, / info {2}\[votoscope-web\] i$/);
});
