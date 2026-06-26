# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Project Overview

**StockSense** is a comprehensive stock research platform built as a Python monorepo. It combines data engineering, AI-powered analysis, and interactive web interfaces to provide stock market insights and research capabilities.

### Architecture

The platform consists of four main components:

1. **Core Library** (`core/`): Shared business logic, data access layer, AI utilities, and technical analysis strategies
2. **StockDB API** (`stockdb/`): FastAPI-based REST API service for stock data operations and bulk processing
3. **StockSense App** (`stocksense-app/`): Reflex-based interactive web application for user interfaces
4. **StockSense AI** (`stocksense-ai/`): Agno based LLM application for all AI agentic capabilities
5. **Snapshot Automation** (`snapshot/`): Data compression/decompression utilities for efficient storage

### Technology Stack

- **Language**: Python 3.13+
- **Package Management**: uv (fast Python package installer and resolver)
- **Data Processing**: Polars (high-performance DataFrames), DuckDB (embedded analytics)
- **AI Framework**: Primarily Agno agents for agentic workflows and Agno's AgentOS for LLM serving API
- **Web Framework**: Reflex (Python-based reactive web framework)
- **API Framework**: FastAPI with Scalar documentation
- **Observability**: Agno's native observability for AI/LLM tracing
- **Database**: Delta Lake (primary), PostgreSQL 17 (only limited to Agno)
- **Containerization**: Docker with Docker Compose orchestration

## Building and Running

### Prerequisites

- Python 3.13 or higher
- uv package manager (`pip install uv`)
- Docker and Docker Compose (for full stack deployment)

### Local Development Setup

#### 1. Core Library Development

```bash
cd core/
uv sync
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pytest tests/
```

#### 2. StockDB API Service

```bash
cd stockdb/
uv sync
uv run python main.py
# API will be available at http://localhost:8080
# Interactive docs at http://localhost:8080/docs
```

#### 3. StockSense Web Application

```bash
cd stocksense-app/
uv sync
uv run reflex run
# App will be available at http://localhost:3000
```

#### 4. StockSense AI Application

```bash
cd stocksense-ai/
uv sync
uv run fastapi dev main
# App will be available at http://localhost:8000
```

#### 5. Full Stack with Docker Compose

```bash
# From repository root
docker-compose up
# Services:
# - StockDB API: http://localhost:8080
# - Agno AgentOS: http://localhost:9000
# - PostgreSQL: localhost:5432
```

### Running Tests

Each component has its own test suite:

```bash
# Core library tests
cd core/ && pytest tests/

# StockDB API tests
cd stockdb/ && pytest tests/

# Run specific test categories
pytest tests/tests_data/        # Data layer tests
pytest tests/tests_strategy/    # Strategy tests
```

## Development Conventions

### Code Organization

- **Monorepo Structure**: Each major component (`core/`, `stockdb/`, `stocksense-app/`, `stocksense-ai/`) is independently versioned with its own `pyproject.toml`
- **Shared Logic**: Common utilities and business logic reside in `core/src/stocksense/` and are imported by other components
- **Type Safety**: Use type hints throughout; `py.typed` marker enables type checking for the core library
- **Configuration**: Centralized configuration via `config.toml` with environment-aware path resolution (see `core/src/stocksense/config.py`)

### API Development (StockDB)

- **Router Organization**: Group endpoints by domain in `stockdb/api/routers/` (e.g., `per_security.py`, `bulk.py`, `strategy.py`, `agents.py`)
- **Models**: Define Pydantic models in `stockdb/api/models.py` for request/response validation
- **Dependencies**: Use FastAPI dependency injection pattern (see `stockdb/api/dependency/`)
- **Documentation**: Endpoints auto-documented via Scalar at `/docs`

### Web Application (Reflex)

- **Page Structure**: Organize pages by feature in `stocksense-app/webapp/pages/` (e.g., `ai/`, `playground/`, `management/`)
- **State Management**: Define reactive state classes in `stocksense-app/webapp/state/`
- **Components**: Reusable UI components in `stocksense-app/webapp/components/`
- **Assets**: Static files in `stocksense-app/assets/`
- **Styling**: Use Reflex's built-in styling props and theming for consistency

### AI Agent Development

- **Agent Definitions**: Define agents in `stocksense-ai/app/agents/_definitions.py` using Agno framework
- **Prompt Management**: Store prompts as YAML in `stocksense-ai/app/prompt/` and load via `PromptManager`
- **Tools/Skills**: Implement agent tools in `stocksense-ai/app/skills/tools/`

### Data Pipeline Patterns

- **ETL Scripts**: Place in `stockdb/pipeline/` (e.g., `ticker_history_data_download.py`)
- **Database Access**: Use `StockDataDB` class from `core/src/stocksense/data/_db.py` for consistent data access
- **Data Sources**: NSE data via `core/src/stocksense/data/_nse.py`, Yahoo Finance via `_yahoo.py`
- **Storage**: Data stored in Deltalake format via Polars for efficient columnar access

### Configuration Management

The platform uses a sophisticated configuration system (`core/src/stocksense/config.py`):

- **Environment Detection**: Automatically detects Docker vs. local execution
- **Path Resolution**: Translates Docker mount paths to OS-appropriate local paths
- **Config Discovery**: Searches for `config.toml` in multiple locations (CWD, parent dirs, env vars)
- **Environment Variables**: Override config via `CONFIG_FILE` or nested env vars (e.g., `COMMON__PHOENIX_URL`)

### Testing Practices

- **Test Organization**: Mirror source structure in `tests/` directories
- **Async Testing**: Use `pytest-asyncio` for async code
- **Coverage**: Aim for comprehensive coverage of business logic and data operations
- **Fixtures**: Define reusable fixtures for database connections and test data

## Integration Points

### Internal Communication

- **App → API**: Web application calls StockDB API via HTTP (configured in `app.stockdb.stockdb_url`)
- **Shared Core**: All components import from `stocksense-core` package
- **Database**: PostgreSQL shared between services (multiple databases: `stockdb`, `agno`)

### External Dependencies

- **Data Sources**: NSE (via nsetools), Yahoo Finance (via yfinance)
- **AI Providers**: OpenAI, Anthropic, Google, Groq, OpenRouter, Ollama (configured in `config.toml`)
- **Observability**: Agno trace for LLM tracing (Agno built-in)

### Docker Volumes

- **Shared Data**: `sra-shared-data` volume mounted at `/shared` in containers
- **Config**: `config.toml` mounted into containers for configuration
- **Persistence**: PostgreSQL data, Phoenix working directory, and stock data persist in shared volume

## Key Architectural Decisions

### Why Polars over Pandas?

- **Performance**: 10-100x faster for large datasets
- **Memory Efficiency**: Lazy evaluation and columnar storage
- **Type Safety**: Strong typing with schema validation
- **Modern API**: Expressive query syntax with method chaining

### Why Reflex for Web UI?

- **Pure Python**: No JavaScript required, full-stack Python development
- **Reactive**: Automatic UI updates on state changes
- **Type-Safe**: Leverages Python type hints for compile-time checks
- **Component-Based**: Reusable components with props and state

### Why Agno?

- **Type-Safe Agents**: Pydantic models for structured outputs
- **Tool Integration**: Easy function-to-tool conversion
- **Multi-Model**: Unified interface across LLM providers
- **Observability**: Built-in tracing and debugging

### Configuration Strategy

- **Single Source of Truth**: `config.toml` for all configuration
- **Environment Aware**: Automatic path translation for Docker vs. local
- **Hierarchical**: Nested sections for logical grouping
- **Override Friendly**: Environment variables for deployment-specific overrides

## Common Workflows

### Adding a New API Endpoint

1. Define Pydantic models in `stockdb/api/models.py`
2. Create router function in appropriate file under `stockdb/api/routers/`
3. Include router in `stockdb/main.py`
4. Test endpoint via Scalar docs at `/docs`

### Creating a New Reflex Page

1. Create page file in `stocksense-app/webapp/pages/<feature>/`
2. Define state class in `stocksense-app/webapp/state/`
3. Import and register page in `stocksense-app/webapp/webapp.py`
4. Add navigation entry in `stocksense-app/webapp/components/nav_config.py`

### Implementing a New AI Agent

1. Define prompt YAML in `stocksense-ai/app/prompt/`
2. Create agent in `stocksense-ai/app/agents/_definitions.py`
3. Implement tools in `stocksense-ai/app/skills/tools/`
4. Expose via API endpoint using Agno's AgentOS

### Adding a Technical Analysis Strategy

1. Implement strategy in `core/src/stocksense/strategy/`
2. Register in strategy catalog
3. Add tests in `core/tests/tests_strategy/`
4. Document in strategy selector agent prompts

## Important Files

- `config.toml`: Central configuration (not in repo, create from template)
- `docker-compose.yml`: Multi-service orchestration definition
- `core/src/stocksense/config.py`: Configuration resolution logic
- `stockdb/main.py`: API service entry point
- `stocksense-app/webapp/webapp.py`: Web app entry point
- `.github/copilot-instructions.md`: Additional AI agent guidance

## Security Considerations

- **API Keys**: Store in `config.toml` (gitignored), never hardcode
- **Database Credentials**: Use environment variables in production
- **CORS**: Configure appropriately for production deployments
- **Input Validation**: All API inputs validated via Pydantic models

## Performance Optimization

- **Lazy Evaluation**: Use Polars lazy API for large datasets
- **Async Operations**: FastAPI endpoints use async/await for I/O
- **Caching**: Agent sessions cached for conversation continuity
- **Batch Processing**: Bulk endpoints for efficient multi-ticker operations

## Troubleshooting

### Config File Not Found

Ensure `CONFIG_FILE` environment variable points to valid `config.toml`, or run from repository root where config can be discovered.

### Docker Volume Permissions

If encountering permission issues, check that shared volume has appropriate ownership for container users.

### Port Conflicts

Default ports: 8080 (API), 3000 (App), 5432 (PostgreSQL), 9000 (Agno AgentOS). Modify in `config.toml` or `docker-compose.yml` if conflicts occur.

### Import Errors

Ensure virtual environment is activated and dependencies installed via `uv sync`. For cross-component imports, verify `stocksense-core` is properly installed.

## Additional Resources

- **Polars Documentation**: <https://docs.pola.rs/>
- **Reflex Documentation**: <https://reflex.dev/docs/>
- **FastAPI Documentation**: <https://fastapi.tiangolo.com/>
- **Agno Documentation**: <https://docs.agno.com/>
- **Pydantic-AI Documentation**: <https://ai.pydantic.dev/>

---

**For AI Agents**: When working with this codebase, prioritize existing patterns and utilities over creating new abstractions. Reference the directory structure and key files above to understand the project layout. Use the documented workflows for common tasks. Always check `config.py` for configuration requirements and `.github/copilot-instructions.md` for additional context.
