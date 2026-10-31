import { queryRows } from "./db.ts";

export const SQL_LATEST_ELECTION = `
  SELECT election_id, election_type, election_date, election_name,
         census, null_votes, blank_votes, candidature_votes, valid_votes,
         voters, turnout_pct
  FROM gold.election_summary
  ORDER BY election_date DESC
  LIMIT 1`;

export const SQL_NATIONAL_RESULTS = `
  SELECT party_id, party_slug, party_name, party_color, votes, pct
  FROM gold.result_by_area
  WHERE election_id = $1 AND level = 'national'
  ORDER BY votes DESC`;

export const GOLD_SQL: Readonly<Record<string, string>> = Object.freeze({
  latest_election: SQL_LATEST_ELECTION,
  national_results: SQL_NATIONAL_RESULTS,
});

export type ElectionSummary = {
  electionId: number;
  electionType: string;
  electionDate: Date;
  electionName: string | null;
  census: number;
  nullVotes: number;
  blankVotes: number;
  candidatureVotes: number;
  validVotes: number;
  voters: number;
  turnoutPct: number | null;
};

export type NationalResult = {
  partyId: number;
  partySlug: string;
  partyName: string;
  partyColor: string | null;
  votes: number;
  pct: number | null;
};

// pg returns bigint/numeric as strings and date as Date (see design.md §D2).
type ElectionRow = {
  election_id: number;
  election_type: string;
  election_date: Date | string;
  election_name: string | null;
  census: string | number;
  null_votes: string | number;
  blank_votes: string | number;
  candidature_votes: string | number;
  valid_votes: string | number;
  voters: string | number;
  turnout_pct: string | number | null;
};

type NationalResultRow = {
  party_id: number;
  party_slug: string;
  party_name: string;
  party_color: string | null;
  votes: string | number;
  pct: string | number | null;
};

function toNumber(value: string | number): number {
  return typeof value === "number" ? value : Number(value);
}

function toNumberOrNull(value: string | number | null): number | null {
  return value === null ? null : toNumber(value);
}

function toDate(value: Date | string): Date {
  return value instanceof Date ? value : new Date(value);
}

export async function getLatestElection(): Promise<ElectionSummary | null> {
  const rows = await queryRows<ElectionRow>(SQL_LATEST_ELECTION);
  const row = rows[0];
  if (!row) return null;

  return {
    electionId: row.election_id,
    electionType: row.election_type,
    electionDate: toDate(row.election_date),
    electionName: row.election_name,
    census: toNumber(row.census),
    nullVotes: toNumber(row.null_votes),
    blankVotes: toNumber(row.blank_votes),
    candidatureVotes: toNumber(row.candidature_votes),
    validVotes: toNumber(row.valid_votes),
    voters: toNumber(row.voters),
    turnoutPct: toNumberOrNull(row.turnout_pct),
  };
}

export async function getNationalResults(
  electionId: number,
): Promise<NationalResult[]> {
  const rows = await queryRows<NationalResultRow>(SQL_NATIONAL_RESULTS, [
    electionId,
  ]);
  return rows.map((row) => ({
    partyId: row.party_id,
    partySlug: row.party_slug,
    partyName: row.party_name,
    partyColor: row.party_color,
    votes: toNumber(row.votes),
    pct: toNumberOrNull(row.pct),
  }));
}
