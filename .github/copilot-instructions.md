# PaaS Charm AI Coding Agent Instructions

## Project Overview

This is the **paas-charm** library - a companion framework for deploying 12-factor web applications using Juju charms. It provides base classes and utilities to build Kubernetes operators for Flask, Django, FastAPI, Go, Express.js, and Spring Boot applications. The library bridges web frameworks with the Juju ecosystem, handling integrations (databases, Redis, S3, SAML, etc.), migrations, and operational concerns.

## Architecture

### Core Components

- **`src/paas_charm/charm.py`**: `PaasCharm` base class - the foundation for all framework-specific charms. Handles all Juju events, integration lifecycle, and orchestrates service restart logic.
- **`src/paas_charm/app.py`**: `App` class manages workload container lifecycle, environment variable generation, and Pebble service layer configuration.
- **`src/paas_charm/framework.py`**: `FrameworkConfig` base class for framework-specific configuration with secret key validation.
- **`src/paas_charm/charm_state.py`**: `CharmState` aggregates all charm configuration, integrations, and secrets into a single immutable state object.
- **Framework-specific charms**: `src/paas_charm/{flask,django,fastapi,go,expressjs,springboot}/charm.py` extend base classes with framework conventions.
- **Gunicorn support**: `src/paas_charm/_gunicorn/` provides WSGI server support for Python frameworks (Flask, Django).

### Integration Pattern

All external integrations (databases, Redis, S3, RabbitMQ, SAML, OAuth, OpenFGA, etc.) follow this pattern:
1. Wrapper classes in `src/paas_charm/{integration}.py` extend upstream charm libraries (e.g., `PaaSRedisRequires(RedisRequires)`)
2. `IntegrationRequirers` dataclass in `charm_state.py` aggregates all integration instances
3. `App.gen_environment()` transforms integration data to environment variables with prefixes (`POSTGRESQL_DB_*`, `REDIS_*`, etc.)
4. Integration events trigger `restart()` which rebuilds the full environment and restarts services

### Sidecar Pattern

Charms use Kubernetes sidecar pattern:
- **Charm container**: Runs Juju operator logic (this library)
- **App container**: Runs the workload (Flask/Django/etc. app with Pebble entrypoint)
- Communication via Pebble API to manage services, files, and execute migrations

## Development Workflows

### Testing

```bash
# Run all checks (lint, unit, static analysis)
tox

# Format code
tox -e fmt

# Unit tests with coverage (requires charmcraft fetch-libs first)
tox -e unit

# Integration tests (requires Juju model)
tox -e integration

# Integration tests for specific framework
tox -e integration -- tests/integration/flask/
```

**Critical**: Integration tests require `charmcraft fetch-libs` to be run in `examples/*/charm/` directories to pull upstream charm libraries. The tox lint/unit environments do this automatically.

### Adding a New Framework

See `CONTRIBUTING.md` "Add a framework" section. Key steps:
1. Create `src/paas_charm/{framework}/charm.py` extending `PaasCharm` or `GunicornBase`
2. Define `FrameworkConfig` subclass with framework-specific configuration fields
3. Add to `examples/{framework}/` with sample app + charm
4. Coordinate with Rockcraft (OCI image) and Charmcraft (profile/extension) repositories

### Adding a New Integration

See `CONTRIBUTING.md` "Add an integration" section. Pattern:
1. Create `src/paas_charm/{integration}.py` wrapper around upstream charm library
2. Initialize in `PaasCharm.__init__()` and observe events
3. Add to `IntegrationRequirers` dataclass
4. Implement `generate_{integration}_env()` in `app.py`
5. Update all framework documentation

## Code Conventions

### Configuration Management

- **User config**: Charm config options (from `charmcraft.yaml`) in `CharmState.user_defined_config`
- **Framework config**: Framework-specific options (e.g., `flask-debug`) validated via Pydantic models
- **Secret handling**: Use `config_get_with_secret()` to transparently handle both regular config and Juju secrets
- **Environment prefixes**: 
  - User config: `APP_*` (configurable via `configuration_prefix`)
  - Framework config: `FLASK_*`, `DJANGO_*`, etc. (via `framework_config_prefix`)
  - Integrations: No prefix by default (via `integrations_prefix`)

### Service Lifecycle

The `restart()` method in `PaasCharm` is the single entry point for all service updates:
1. Check `is_ready()` - validates integrations, secret storage, OAuth client
2. Set migration status to pending if `rerun_migrations=True`
3. Call `App.restart()` which:
   - Builds Pebble layer with `_app_layer()`
   - Runs `_prepare_service_for_restart()` (framework hook)
   - Executes database migrations via `_run_migrations()`
   - Calls `container.replan()`
4. Update ingress and set `ActiveStatus`

### Database Migrations

Migrations run automatically on container start if any of these files exist in `app_dir`:
- `migrate` (executable)
- `migrate.sh` (bash script)
- `migrate.py` (Python script)
- `manage.py` (Django - runs `python3 manage.py migrate`)

Migration state tracked in `/tmp/{framework}/state/` to prevent re-running on every restart unless `rerun_migrations=True`.

### Error Handling

- **Pydantic validation errors**: Caught in `get_framework_config()` and `_create_charm_state()`, converted to `CharmConfigInvalidError`
- **Decorator pattern**: `@block_if_invalid_data` on event handlers catches `CharmConfigInvalidError` and sets `BlockedStatus`
- **Missing integrations**: `_missing_required_integrations()` checks metadata for non-optional relations and blocks if absent

### Testing Structure

- **Unit tests**: `tests/unit/{framework}/` - mock Juju and test logic in isolation
- **Integration tests**: `tests/integration/{framework}/` - deploy real charms to Juju model
- **Fixtures**: `tests/integration/conftest.py` provides `ops_test`, image building, charm config injection
- **Helper**: `tests/integration/helpers.py` has `inject_charm_config()` for testing non-optional configs

## Key Files to Reference

- **Examples**: `examples/{flask,django}/charm/src/charm.py` - minimal charm implementations
- **Documentation**: `docs/explanation/charm-architecture.rst` - C4 diagrams and event flow
- **Gunicorn config**: `src/paas_charm/_gunicorn/webserver.py` - worker class validation and configuration
- **Database utilities**: `src/paas_charm/databases.py` - creates multiple database requirers (PostgreSQL, MySQL, MongoDB)

## Common Pitfalls

- **Forgetting `charmcraft fetch-libs`**: Charm libraries are not vendored; must be fetched before running tests
- **Breaking backward compatibility**: Optional integrations (marked `optional: true` in metadata) must remain optional
- **Environment variable conflicts**: User config takes precedence over framework config, but framework config keys are reserved
- **Worker/scheduler services**: Background services (ending in `-worker` or `-scheduler`) automatically get environment variables; schedulers only run on unit/0
- **Integration event ordering**: Database events include `database_created` AND `endpoints_changed` - both trigger restarts with `rerun_migrations=True`

## Package Structure

```
src/paas_charm/
├── charm.py              # PaasCharm base class
├── app.py                # App workload manager
├── framework.py          # FrameworkConfig base
├── charm_state.py        # CharmState aggregator
├── _gunicorn/            # WSGI server support
│   ├── charm.py          # GunicornBase for Python frameworks
│   └── webserver.py      # Gunicorn configuration
├── {integration}.py      # Integration wrappers (redis, s3, saml, etc.)
└── {framework}/          # Framework-specific implementations
    └── charm.py
```

## Quick Reference

- **Line length**: 99 characters (Black/isort configured)
- **Python version**: 3.10+ required
- **Coverage target**: 90% minimum
- **Docstring style**: Google format
- **Type hints**: Required for all public APIs (`mypy` enforced)
