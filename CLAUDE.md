# Claude Instructions

## Read docs before reading source files

Before reading any source file in this project, read the core documentation files under `docs/` first:

1. `docs/ARCHITECTURE.md` — system overview, layers, job lifecycle, database schema, configuration
2. `docs/CODEBASE.md` — file-by-file reference, key functions, dependency list
3. `docs/FEATURES.md` — current features, known bugs (with file:line refs), future roadmap
4. `docs/models_setup.md` — model download status, required paths, Windows compatibility patch

For setup and operational context, also available:

- `docs/installation.md` — full Windows + NVIDIA GPU setup guide
- `docs/app_overview.md` — app-level overview and quick-start
- `docs/backend_api.md` — API endpoint reference
- `docs/bootstrap_online.md` — one-time online bootstrap steps
- `docs/package_offline.md` — offline runtime packaging
- `docs/pipeline_spec.md` — original implementation spec and current build status
- `docs/audit.md` — detailed audit report: all bugs with root causes and fix instructions, security issues, performance issues, code quality gaps, and future scope

Reading the core four files first gives a complete picture of the codebase and eliminates most exploratory reads of source files. Only open a source file when you need implementation-level detail not covered by the docs.

## Keep docs in sync with code changes

Whenever you make a code change — bug fix, new feature, refactor — update every doc file where that change is reflected:

- **Bug fixed** → remove it from the Bugs section of `docs/FEATURES.md`; update relevant descriptions in `docs/ARCHITECTURE.md` or `docs/CODEBASE.md` if the fix changes how a component works.
- **New feature added** → add it to the Current Features section of `docs/FEATURES.md`; update `docs/ARCHITECTURE.md` if the architecture changed; update `docs/CODEBASE.md` with any new files or functions.
- **New runtime adapter** → update the adapter list in `docs/ARCHITECTURE.md` and the adapter section of `docs/CODEBASE.md`.
- **New env var or config field** → update the configuration table in `docs/ARCHITECTURE.md`.
- **Future scope item implemented** → move it from the Future Scope section of `docs/FEATURES.md` to Current Features.
- **Model download status changed** → update the checklist table in `docs/models_setup.md`.
- **Setup steps changed** → update `docs/installation.md` and/or `docs/bootstrap_online.md`.
- **API endpoints added or changed** → update `docs/backend_api.md`.

Do not leave docs stale after a code change. Update the docs in the same response as the code change.
