---
name: harness-cli
description: Operate the harness CLI safely — init, sync and doctor — including copy-only installs, project-owned versus shared assets, legacy symlink migration, preflight failures, exit codes, and verification. Use when asked to link or install the harness into a project (sibling, nested or absolute), refresh an existing install, diagnose a target, migrate an older link install, or explain what harness init/sync/doctor will change.
---

# Harness CLI

The CLI lives at `<harness-repo>/bin/harness`. Installs are copy-only: it creates
physical copies and never symlinks. It also never mutates git or GitHub state;
commits and pushes need separate explicit approval.

## Command map

```bash
harness init [TARGET] [--name NAME] [--description TEXT]
             [--with data-model,data-sources] [--force]
harness sync [TARGET]
harness doctor [TARGET] [--run-checks] [--strict]
harness --version
```

`TARGET` defaults to `.` and is resolved to an absolute path.

| Command | Effect |
| --- | --- |
| `init` | Create the target if missing. Add missing project files, shared copies, `.harness/bin/validate.py` and `.harness/schema/*`. Existing real files are skipped; existing symlinks are replaced by copies. |
| `sync` | Refresh shared copies only. Project-owned files and `specs/_template` are kept. Missing `.harness` is restored. |
| `doctor` | Run the validator. `--run-checks` also runs configured `setup` and `checks`; `--strict` turns warnings into failure. |
| `init --force` | Overwrite project-owned and shared files. Destructive; require explicit approval and a backup. |

`init` does not refresh shared files that already exist as real copies; use
`sync` for that. `init` does replace legacy symlinks with copies.

## Inspect the target

Resolve the absolute path and read its state before writing:

```bash
PROJECT=/absolute/path/to/project
if git -C "$PROJECT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git -C "$PROJECT" status --porcelain
  git -C "$PROJECT" branch --show-current
else
  echo "not a git repository: skip git checks; do not run git init without approval"
fi
```

A new/empty target may not be a git repository yet. That is not an installer
error; report it and skip the git checks. Never run `git init` without approval.

## Output legend

- `[create]` project file rendered from a template.
- `[copy]` shared file copied (or a legacy symlink replaced).
- `[skip]` existing real file kept; use `sync` or `--force` to change it.
- `[unlink]` legacy symlink or stale `VENDOR` marker removed.
- `[warn]` non-fatal issue, usually `.harness/` still in `.gitignore`.

Exit codes: `0` success, `1` validation/preflight/usage failure, `2` invalid
command-line arguments.

## Safety rules

1. Inspect before writing: `git status` and branch when the target is a git
   repository, plus which harness files already exist. Skip git checks for a
   non-repository target; do not initialize one without approval.
2. Never use `--force` without the user's explicit approval. It overwrites
   `AGENTS.md`, `feature_list.json`, `harness.config.json`, `opencode.json`,
   `.agents/*` docs, `progress/current.md` and `progress/history.md`.
3. `.harness/` must be committed, not ignored. If `.gitignore` still lists it,
   the installer warns; remove the entry.
4. No symlinks are created. Check only harness-managed paths for links; unrelated
   project symlinks such as virtualenvs are fine.
5. Do not commit, push, tag or open PRs from this skill.

## Link a new project

```bash
PROJECT=/absolute/path/to/project
HARNESS=/absolute/path/to/harness-repo/bin/harness

"$HARNESS" init "$PROJECT" --name my-project --description "One line."
```

For a brand-new/empty directory this creates the full install. Configure the
project before calling it configured:

- `harness.config.json`: real `setup` and at least one required `checks` entry.
  Empty checks fail `./init.sh`.
- `.agents/architecture.md`, `conventions.md`, `style.md`, `environment.md`,
  `status.md`: project facts.
- `AGENTS.md`: adapt the constitution/router; keep the hard rules.

Verify:

```bash
"$HARNESS" doctor "$PROJECT"
(cd "$PROJECT" && ./init.sh)
git -C "$PROJECT" status --short   # only if the target is a git repository
```

## Link an existing project

An existing project may already have its own `AGENTS.md`, `init.sh`, agents,
specs and queue. Prefer an additive install:

```bash
"$HARNESS" init "$PROJECT" --name <existing-name>
```

It adds missing files only. Capture every `[skip]` line and report it: those
files were not merged. If the project keeps its own `init.sh`, the new
`harness.config.json` and `.harness/` are installed but its gate may still be
the old one; merging the gate is a separate, explicit change.

Do not run `sync` immediately after an additive install unless the user wants
shared files refreshed; `sync` would replace the project's existing shared
files with the harness versions.

## Update an existing install

```bash
"$HARNESS" sync "$PROJECT"
"$HARNESS" doctor "$PROJECT"
```

`sync` refreshes `CHECKPOINTS.md`, `init.sh`, `.agents/specs.md`, shared skills,
agents, commands, the validator and schemas. It keeps `AGENTS.md`,
`feature_list.json`, `harness.config.json`, `opencode.json`, `.agents/*` topic
docs, `progress/` and `specs/`. It intentionally does not refresh
`specs/_template`.

## Diagnose

```bash
"$HARNESS" doctor "$PROJECT"                 # structure only
"$HARNESS" doctor "$PROJECT" --run-checks    # structure + setup + checks
"$HARNESS" doctor "$PROJECT" --strict        # warnings fail too
```

`doctor` needs `<target>/.harness/bin/validate.py`. If it reports the validator
missing, run `init` or `sync` first. Running it on the harness source repository
uses `bin/validate.py` instead.

## Migrate a legacy link install

Older installs used `.harness` and shared-file symlinks. No manual conversion is
needed:

```bash
"$HARNESS" init "$PROJECT"
# or, to refresh shared copies too:
"$HARNESS" sync "$PROJECT"
```

`init`/`sync` unlink the `.harness` symlink before writing, replace shared
symlinks with copies and drop a stale `.harness/VENDOR` marker. Never copy or
edit through a legacy `.harness` symlink; it points back at the harness source.

## Verify an install

Check every path the installer wrote for symlinks; this list is the minimum:

```bash
for p in .harness .agents .opencode AGENTS.md CHECKPOINTS.md \
         harness.config.json feature_list.json init.sh opencode.json \
         progress specs; do
  [ -L "$PROJECT/$p" ] && echo "unexpected symlink: $p"
done
find "$PROJECT/.harness" "$PROJECT/.agents" "$PROJECT/.opencode" \
     "$PROJECT/progress" "$PROJECT/specs" -type l -print
```

Use a variable name other than `path`: zsh ties `path` to `PATH`, so a
`for path in ...` loop breaks the rest of the commands.

Ignore unrelated project symlinks (for example a virtualenv). `doctor` validates
structure; without `--run-checks` it reports how many checks are configured but
does **not** execute them. Use `--run-checks` or `./init.sh` to run them.

Then confirm the gate and, when applicable, the working tree:

```bash
(cd "$PROJECT" && ./init.sh)
git -C "$PROJECT" status --short   # only if the target is a git repository
```

If the target is not a git repository, skip the last line and say so.

## Preflight and failure handling

The CLI fails before writing when:

- `--with` names an unknown optional doc;
- a destination that must be a file is a directory;
- `.harness` exists as a regular file or other non-directory;
- the target path is a file, not a directory.

Fix the argument or target; do not delete project files to force the install.
`--mode link|vendor` was removed and is rejected with exit code 2.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| `validator not found` | Run `harness init` or `harness sync` in the target. |
| `no checks configured` from `./init.sh` | Add at least one required check to `harness.config.json`. |
| `.gitignore ignores .harness/` warning | Remove the entry so the copies are committed. |
| Existing files reported `[skip]` | Merge manually, or use `--force` only with approval. |
| Old symlinks still present | Run `init` or `sync`; the CLI replaces them. |
| `sync` did not update project docs | Expected: project-owned files are never overwritten. |

## Report

Return the target path, command, exit code, and a table:

| Change | Paths |
| --- | --- |
| Created | ... |
| Copied / refreshed | ... |
| Skipped (needs merge) | ... |
| Warnings | ... |

State whether `doctor` and the project gate passed, and whether the target's
existing `init.sh` is the harness gate or its own. Do not claim the project is
linked if checks are empty or the gate is red.

"Linked" means installed and the gate is green. "Configured" means the checks
and project docs are filled; an install alone is not configuration.
