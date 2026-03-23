"""Shared fixtures and pytest configuration for the full test suite.

This conftest.py is discovered at the tests/ root level, making its fixtures
available to all test subdirectories.

Unit tests (tests/hook_tracer/, tests/telemetry/) always run.
Integration tests (tests/integration/) skip gracefully when the OTel stack
environment variables are not configured.
"""
from __future__ import annotations

import os

import pytest


# ---------------------------------------------------------------------------
# OTel-gating fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def otel_configured():
    """Skip the calling test if OTel environment variables are not set.

    Usage in a test that requires a live OTel collector::

        def test_something(otel_configured):
            # this line is only reached when env vars are present
            ...

    The two required env vars are:
      - CLAUDE_CODE_ENABLE_TELEMETRY=1
      - OTEL_EXPORTER_OTLP_ENDPOINT  (any non-empty value)
    """
    telemetry_enabled = os.environ.get("CLAUDE_CODE_ENABLE_TELEMETRY") == "1"
    endpoint_set = bool(os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip())

    if not telemetry_enabled or not endpoint_set:
        pytest.skip(
            "OTel env vars not configured "
            "(need CLAUDE_CODE_ENABLE_TELEMETRY=1 and OTEL_EXPORTER_OTLP_ENDPOINT)"
        )


# ---------------------------------------------------------------------------
# Marker registration (supplement to pytest.ini)
# ---------------------------------------------------------------------------


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: mark test as an integration test requiring a live OTel stack.",
    )
