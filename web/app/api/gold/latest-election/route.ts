import { getLatestElection } from "../../_lib/gold.ts";
import { logger } from "../../../../lib/logging.ts";

export const dynamic = "force-dynamic";

const NO_STORE = { "Cache-Control": "no-store" };

export async function GET(): Promise<Response> {
  try {
    const election = await getLatestElection();
    return Response.json({ election }, { headers: NO_STORE });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    logger.error(`GET /api/gold/latest-election failed: ${message}`);
    return Response.json(
      { error: "internal" },
      { status: 500, headers: NO_STORE },
    );
  }
}
