import pg from "pg";

import { logger } from "../../../lib/logging.ts";

let pool: pg.Pool | undefined;

/** Lazily create the pool: importing this module never touches the database. */
export function getPool(): pg.Pool {
  const connectionString = process.env.DATABASE_URL;
  if (!connectionString) {
    throw new Error("DATABASE_URL is not set");
  }
  pool ??= new pg.Pool({
    connectionString,
    application_name: "votoscope-web",
  });
  return pool;
}

/**
 * Run one parameterised query and log SQL/row count at debug and failures at
 * error. Never logs the connection string or credentials (R13).
 */
export async function queryRows<T>(
  text: string,
  params: unknown[] = [],
): Promise<T[]> {
  const startedAt = Date.now();
  try {
    const result = await getPool().query(text, params);
    const sql = text.replace(/\s+/g, " ").trim();
    logger.debug(
      `sql=${sql} rows=${result.rowCount ?? 0} duration_ms=${Date.now() - startedAt}`,
    );
    return result.rows as T[];
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    logger.error(`sql failed: ${message}`);
    throw error;
  }
}
