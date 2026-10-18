#!/usr/bin/env bash
# init.sh — Verificación e inicialización del entorno.
#
# Este script lo ejecuta el agente al COMENZAR una sesión y antes de
# declarar cualquier feature como `done`. Si falla, la sesión no avanza.

set -u
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

ok()    { printf "${GREEN}[OK]${NC}    %s\n" "$1"; }
warn()  { printf "${YELLOW}[WARN]${NC}  %s\n" "$1"; }
fail()  { printf "${RED}[FAIL]${NC}  %s\n" "$1"; }

EXIT_CODE=0

echo "── 1. Verificando entorno ─────────────────────────────"

if ! command -v uv >/dev/null 2>&1; then
  fail "uv no está instalado (https://docs.astral.sh/uv/)"
  exit 1
fi
ok "uv -> $(uv --version)"

echo ""
echo "── 2. Verificando archivos base del arnés ──────────────"

for f in AGENTS.md feature_list.json CHECKPOINTS.md progress/current.md progress/history.md \
         .agents/specs.md opencode.json \
         .opencode/agents/leader.md .opencode/agents/spec-author.md \
         .opencode/agents/implementer.md .opencode/agents/reviewer.md; do
  if [ ! -f "$f" ]; then
    fail "Falta archivo base: $f"
    EXIT_CODE=1
  else
    ok "Existe $f"
  fi
done

echo ""
echo "── 3. Validando feature_list.json y specs ─────────────"

python3 - <<'PY'
import json, os, sys
try:
    data = json.load(open("feature_list.json"))
    valid = {"pending", "spec_ready", "in_progress", "done", "blocked"}
    in_progress = [f for f in data["features"] if f["status"] == "in_progress"]
    if len(in_progress) > 1:
        print(f"[FAIL]  Hay {len(in_progress)} features en in_progress (máximo 1)")
        sys.exit(1)
    requires_spec = {"spec_ready", "in_progress", "done"}
    spec_errors = []
    for f in data["features"]:
        if f["status"] not in valid:
            print(f"[FAIL]  Estado inválido en feature {f['id']}: {f['status']}")
            sys.exit(1)
        if f.get("sdd") and f["status"] in requires_spec:
            spec_dir = os.path.join("specs", f"{f['id']:03d}_{f['name']}")
            for fname in ("requirements.md", "design.md", "tasks.md"):
                if not os.path.isfile(os.path.join(spec_dir, fname)):
                    spec_errors.append(
                        f"feature {f['id']} ({f['name']}) en {f['status']} "
                        f"sin {spec_dir}/{fname}"
                    )
    if spec_errors:
        for e in spec_errors:
            print(f"[FAIL]  {e}")
        sys.exit(1)
    print(f"[OK]    feature_list.json válido ({len(data['features'])} features)")
    print("[OK]    Specs presentes para features sdd con estado no-pending")
except SystemExit:
    raise
except Exception as e:
    print(f"[FAIL]  feature_list.json o specs inválidos: {e}")
    sys.exit(1)
PY

if [ $? -ne 0 ]; then EXIT_CODE=1; fi

echo ""
echo "── 4. Ingestador: sync, lint y tests ───────────────────"

if [ ! -d ingestor ]; then
  fail "Falta la carpeta ingestor/"
  EXIT_CODE=1
else
  if (cd ingestor && uv sync --quiet); then
    ok "uv sync"
  else
    fail "uv sync falló"
    EXIT_CODE=1
  fi
  if (cd ingestor && uv run ruff check . --quiet); then
    ok "ruff check"
  else
    fail "ruff check con errores"
    EXIT_CODE=1
  fi
  if (cd ingestor && uv run ruff format --check . --quiet); then
    ok "ruff format"
  else
    fail "ruff format con diferencias"
    EXIT_CODE=1
  fi
  if (cd ingestor && uv run pytest -q); then
    ok "pytest: todos los tests pasan"
  else
    fail "pytest: hay tests rotos"
    EXIT_CODE=1
  fi
fi

echo ""
echo "── 5. Drift del modelo (si la base responde) ───────────"

# El Postgres es compartido (host 5434); puede estar levantado desde otro
# checkout/worktree, por eso se comprueba el puerto y no el proyecto compose.
if nc -z localhost 5434 2>/dev/null; then
  if (cd ingestor && uv run alembic check); then
    ok "alembic check: sin drift"
  else
    fail "alembic check: drift o base sin migrar (uv run alembic upgrade head)"
    EXIT_CODE=1
  fi
else
  warn "Postgres no responde en localhost:5434; se omite alembic check (docker compose up -d --wait)"
fi

echo ""
echo "── 6. Resumen ──────────────────────────────────────────"

if [ $EXIT_CODE -eq 0 ]; then
  ok "Entorno listo. Puedes empezar a trabajar."
else
  fail "El entorno NO está listo. Resuelve los errores antes de avanzar."
fi

exit $EXIT_CODE
