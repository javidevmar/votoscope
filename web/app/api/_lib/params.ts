/** Validate an `electionId` query parameter: a positive integer or a RangeError. */
export function parseElectionId(raw: string | null): number {
  if (raw === null || !/^\d+$/.test(raw)) {
    throw new RangeError(`invalid electionId: ${raw}`);
  }
  const value = Number(raw);
  if (!Number.isSafeInteger(value) || value <= 0) {
    throw new RangeError(`invalid electionId: ${raw}`);
  }
  return value;
}
