# Copilot Instructions for Stock Research Platform

## Project Architecture
- **Monorepo Structure**: Contains `core`, `stockdb`, `webapp`, and `snapshot` directories, each with its own `pyproject.toml` and codebase.
- **Core Logic**: Business logic and utilities are in `core/src/stocksense/`.
- **API Service**: `stockdb/api/` provides FastAPI endpoints, with routers in `routers/` and models in `models.py`.
- **Web Application**: `webapp/app/` contains the Reflex-based frontend, with pages in `pages/` and shared logic in `core/`.
- **Snapshot Automation**: `snapshot/` scripts handle data compression/decompression and automation tasks.

## Developer Workflows
- **Python Environments**: Each major directory may use its own virtual environment. Activate with `.venv/Scripts/Activate.ps1` (Windows).
- **Build/Run Webapp**: Use the VS Code task `reflex app` or run `uv run reflex run` from `webapp/`.
- **API Service**: Start FastAPI from `stockdb/main.py` (see Dockerfile for container usage).
- **Testing**: Tests are in `tests/` subfolders within each component. Use `pytest` from the respective directory.
- **Docker Compose**: Use `docker-compose.yml` at the repo root for multi-service orchestration.

## Project-Specific Patterns
- **Modular Imports**: Utilities and shared logic are imported from `core/src/stocksense/`.
- **Router Organization**: API endpoints are grouped by domain in `stockdb/api/routers/` (e.g., `per_security.py`, `tasks.py`).
- **Data Pipelines**: ETL and table creation scripts are in `stockdb/pipeline/`.
- **Frontend Pages**: Streamlit pages are organized by feature in `webapp/app/pages/` (e.g., `ai/`, `playground/`).

## Integration Points
- **Internal Communication**: Webapp interacts with API via HTTP endpoints defined in `stockdb/api/routers/`.
- **External Dependencies**: See each `pyproject.toml` for required packages. Dockerfiles specify runtime dependencies.
- **Automation**: PowerShell and Bash scripts in `snapshot/` automate data tasks.

## Conventions
- **Type Hints**: Use type hints in Python code for clarity and tooling support.
- **Tests**: Place tests in `tests/` folders, mirroring source structure.
- **Configuration**: Use `config.py` or `config.toml` for settings; avoid hardcoding.

## Key Files & Directories
- `core/src/stocksense/`: Core business logic library used in all downstream components
- `stockdb/api/routers/`: API endpoint definitions
- `webapp/app/pages/`: Reflex frontend pages
- `docker-compose.yml`: Multi-service orchestration
- `snapshot/automation.ps1`: Data automation script

---

**For AI agents:**
- Prefer existing utilities and patterns over new abstractions.
- Reference the above directories for examples before generating new code.
- Use VS Code tasks and Docker for builds/runs when possible.
- Ask for clarification if workflow or integration details are unclear.
