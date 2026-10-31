import { getLatestElection, getNationalResults } from "@/app/api/_lib/gold.ts";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export const dynamic = "force-dynamic";

const integer = new Intl.NumberFormat("es-ES");
const decimal = new Intl.NumberFormat("es-ES", { maximumFractionDigits: 2 });
const date = new Intl.DateTimeFormat("es-ES", { dateStyle: "long" });

const PARTY_FALLBACK_COLOR = "#6b7280";

export default async function Home() {
  const election = await getLatestElection();

  if (!election) {
    return (
      <main className="mx-auto max-w-4xl px-6 py-12">
        <Card>
          <CardHeader>
            <CardTitle>Sin datos</CardTitle>
            <CardDescription>
              Todavía no hay elecciones cargadas en el esquema gold.
            </CardDescription>
          </CardHeader>
        </Card>
      </main>
    );
  }

  const results = await getNationalResults(election.electionId);
  const summary = [
    { label: "Censo", value: integer.format(election.census) },
    { label: "Votantes", value: integer.format(election.voters) },
    {
      label: "Participación",
      value:
        election.turnoutPct === null
          ? "—"
          : `${decimal.format(election.turnoutPct)} %`,
    },
  ];

  return (
    <main className="mx-auto max-w-4xl space-y-8 px-6 py-12">
      <header className="space-y-2">
        <p className="text-sm text-muted-foreground">Última elección</p>
        <h1 className="text-3xl font-semibold tracking-tight">
          {election.electionName ?? election.electionType}
        </h1>
        <p className="text-muted-foreground">
          {date.format(election.electionDate)}
        </p>
      </header>

      <section className="grid gap-4 sm:grid-cols-3">
        {summary.map((item) => (
          <Card key={item.label}>
            <CardHeader>
              <CardDescription>{item.label}</CardDescription>
              <CardTitle className="text-2xl">{item.value}</CardTitle>
            </CardHeader>
          </Card>
        ))}
      </section>

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold">Resultados nacionales</h2>
          <Button asChild variant="outline" size="sm">
            <a href={`/api/gold/national-results?electionId=${election.electionId}`}>
              Ver JSON
            </a>
          </Button>
        </div>

        <Card>
          <CardContent>
            {results.length === 0 ? (
              <p className="text-muted-foreground">Sin resultados nacionales.</p>
            ) : (
              <ul className="divide-y">
                {results.map((result) => (
                  <li
                    key={result.partyId}
                    className="flex items-center gap-4 py-3"
                  >
                    <span
                      aria-hidden
                      className="size-3 rounded-full"
                      style={{
                        backgroundColor:
                          result.partyColor ?? PARTY_FALLBACK_COLOR,
                      }}
                    />
                    <span className="flex-1 font-medium">
                      {result.partyName}
                    </span>
                    <span className="tabular-nums text-muted-foreground">
                      {integer.format(result.votes)} votos
                    </span>
                    <span className="w-20 text-right tabular-nums">
                      {result.pct === null ? "—" : `${decimal.format(result.pct)} %`}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </section>
    </main>
  );
}
