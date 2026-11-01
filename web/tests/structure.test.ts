import assert from "node:assert/strict";
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));

function read(path: string): string {
  return readFileSync(join(root, path), "utf8");
}

function filesUnder(dir: string): string[] {
  const absolute = join(root, dir);
  if (!existsSync(absolute)) return [];
  return readdirSync(absolute, { withFileTypes: true }).flatMap((entry) => {
    const relative = `${dir}/${entry.name}`;
    return entry.isDirectory() ? filesUnder(relative) : [relative];
  });
}

const pkg = JSON.parse(read("package.json")) as {
  scripts: Record<string, string>;
  dependencies: Record<string, string>;
  devDependencies: Record<string, string>;
  packageManager?: string;
  engines?: Record<string, string>;
};

// SQL keywords / statements, matched case-insensitively.
const SQL_PATTERN =
  /\b(?:select\s+[\s\S]*?\bfrom|insert\s+into|update\s+\w+\s+set|delete\s+from|create\s+(?:table|view|schema|role)|alter\s+(?:table|schema|role)|drop\s+(?:table|view|schema|role)|truncate\s+)/i;
const PG_IMPORT = /(?:from\s+["']pg["']|require\(\s*["']pg["']\s*\))/;

test("package.json: scripts, package manager and approved dependencies", () => {
  for (const script of ["dev", "build", "start", "lint", "test"]) {
    assert.ok(pkg.scripts[script], `falta el script ${script}`);
  }
  assert.match(pkg.packageManager ?? "", /^pnpm@10\.28\./);
  assert.match(pkg.engines?.node ?? "", />=\s*24/);

  for (const dependency of [
    "next",
    "react",
    "react-dom",
    "pg",
    "class-variance-authority",
    "clsx",
    "tailwind-merge",
    "lucide-react",
    "@radix-ui/react-slot",
  ]) {
    assert.ok(pkg.dependencies[dependency], `falta la dependencia ${dependency}`);
  }
  for (const dependency of [
    "typescript",
    "@types/node",
    "@types/react",
    "@types/react-dom",
    "@types/pg",
    "eslint",
    "eslint-config-next",
    "tailwindcss",
    "tw-animate-css",
  ]) {
    assert.ok(pkg.devDependencies[dependency], `falta la devDependency ${dependency}`);
  }
  assert.ok(
    pkg.devDependencies["@tailwindcss/postcss"] ??
      pkg.devDependencies["@tailwindcss/turbopack"],
    "falta el pipeline CSS de Tailwind",
  );

  assert.ok(existsSync(join(root, "pnpm-lock.yaml")), "falta pnpm-lock.yaml");
  assert.ok(
    !existsSync(join(root, "package-lock.json")),
    "no debe haber package-lock.json (gestor: pnpm)",
  );
});

test("App Router: layout, page and the two BFF routes exist", () => {
  assert.ok(existsSync(join(root, "app/layout.tsx")), "falta app/layout.tsx");
  assert.ok(existsSync(join(root, "app/page.tsx")), "falta app/page.tsx");
  assert.ok(
    existsSync(join(root, "app/api/gold/latest-election/route.ts")),
    "falta el Route Handler latest-election",
  );
  assert.ok(
    existsSync(join(root, "app/api/gold/national-results/route.ts")),
    "falta el Route Handler national-results",
  );

  const routes = filesUnder("app")
    .filter((file) => file.endsWith("/route.ts"))
    .sort();
  assert.deepEqual(routes, [
    "app/api/gold/latest-election/route.ts",
    "app/api/gold/national-results/route.ts",
  ]);
});

test("BFF boundary: SQL and pg only under app/api/", () => {
  const outsideBff = [
    ...filesUnder("app").filter((file) => !file.startsWith("app/api/")),
    ...filesUnder("components"),
    ...filesUnder("lib"),
  ].filter((file) => /\.(ts|tsx)$/.test(file));

  for (const file of outsideBff) {
    const source = read(file);
    assert.doesNotMatch(source, SQL_PATTERN, `${file} contiene SQL`);
    assert.doesNotMatch(source, PG_IMPORT, `${file} importa pg`);
    assert.doesNotMatch(source, /\bNEXT_PUBLIC_DATABASE_URL\b/, `${file} expone la URL`);
    assert.doesNotMatch(source, /["']use server["']/, `${file} define Server Actions`);
  }

  const db = read("app/api/_lib/db.ts");
  const gold = read("app/api/_lib/gold.ts");
  assert.match(db, PG_IMPORT, "db.ts debe usar pg");
  assert.match(gold, /\bSELECT\b/i, "gold.ts debe contener el SQL de gold.*");
  assert.match(gold, /\bfrom\s+gold\./i, "gold.ts debe consultar el esquema gold");
});

test("page: Server Component using the BFF service and a shadcn component", () => {
  const page = read("app/page.tsx");
  assert.match(page, /@\/app\/api\/_lib\/gold\.ts/, "la portada importa el servicio del BFF");
  assert.match(page, /@\/components\/ui\//, "la portada usa un componente de shadcn");
  assert.match(
    page,
    /export\s+const\s+dynamic\s*=\s*["']force-dynamic["']/,
    "la portada declara force-dynamic",
  );
  assert.doesNotMatch(page, /["']use client["']/, "la portada no es componente cliente");

  for (const file of filesUnder("lib").filter((path) => /\.(ts|tsx)$/.test(path))) {
    assert.doesNotMatch(read(file), /["']use client["']/, `${file} no puede ser cliente`);
  }
});

test("environment: .env.example with the read-only role, never NEXT_PUBLIC_", () => {
  const env = read(".env.example");
  assert.match(
    env,
    /^DATABASE_URL=postgresql:\/\/votoscope_web:[^@\s]+@localhost:5434\/votoscope$/m,
  );
  assert.match(env, /^LOG_LEVEL=INFO$/m);
  assert.doesNotMatch(env, /NEXT_PUBLIC_DATABASE_URL/);
});

test("UI system: shadcn and Tailwind tokens are configured", () => {
  const components = JSON.parse(read("components.json")) as {
    tailwind?: { css?: string; cssVariables?: boolean };
  };
  assert.equal(components.tailwind?.css, "app/globals.css");
  assert.equal(components.tailwind?.cssVariables, true);
  assert.ok(filesUnder("components/ui").length > 0, "components/ui/ está vacío");

  const utils = read("lib/utils.ts");
  assert.match(utils, /export\s+function\s+cn\b/);

  const css = read("app/globals.css");
  assert.match(css, /@import\s+["']tailwindcss["']/);
  assert.match(css, /--background:/);
  assert.match(css, /--foreground:/);
});
