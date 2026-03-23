# Makefile for software-factory-otel-tracing
#
# Targets:
#   make test             Run full suite (unit + integration; integration skips
#                         gracefully when OTel env vars are absent)
#   make test-unit        Run only unit tests (never requires OTel stack)
#   make test-integration Run only integration tests; fails loudly if OTel is
#                         not configured
#
# Integration tests are gated by two env vars:
#   CLAUDE_CODE_ENABLE_TELEMETRY=1
#   OTEL_EXPORTER_OTLP_ENDPOINT=<grpc endpoint, e.g. http://localhost:4317>
#
# If those vars are unset, integration tests skip automatically in `make test`
# but `make test-integration` will also skip (loudly) if they are missing.

PYTHON ?= python3
PYTEST  = $(PYTHON) -m pytest

# Unit test directories (always run, no external dependencies)
UNIT_TEST_DIRS = tests/hook_tracer tests/telemetry

# Integration test directory (requires live OTel/Jaeger stack)
INTEGRATION_TEST_DIR = tests/integration

.PHONY: test test-unit test-integration

## test: Run the full test suite (unit always + integration with graceful skip)
test:
	$(PYTEST) tests/ -q

## test-unit: Run only the fast, dependency-free unit tests
test-unit:
	$(PYTEST) $(UNIT_TEST_DIRS) -q

## test-integration: Run only integration tests (skips if OTel not configured)
test-integration:
	$(PYTEST) $(INTEGRATION_TEST_DIR) -v
