import { getNationalResults } from "../../_lib/gold.ts";
import { parseElectionId } from "../../_lib/params.ts";
import { logger } from "../../../../lib/logging.ts";

export const dynamic = "force-dynamic";

const NO_STORE = { "Cache-Control": "no-store" };

export async function GET(request: Request): Promise<Response> {
  let electionId: number;
  try {
    electionId = parseElectionId(
      new URL(request.url).searchParams.get("electionId"),
    );
  } catch (error) {
    if (error instanceof RangeError) {
      return Response.json(
        { error: "invalid_election_id" },
        { status: 400, headers: NO_STORE },
      );
    }
    throw error;
  }

  try {
    const results = await getNationalResults(electionId);
    return Response.json({ results }, { headers: NO_STORE });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    logger.error(`GET /api/gold/national-results failed: ${message}`);
    return Response.json(
      { error: "internal" },
      { status: 500, headers: NO_STORE },
    );
  }
}
