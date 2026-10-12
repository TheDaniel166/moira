"""Truthfulness tests for the generated Light Box current status."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).parents[2]
SCRIPT = REPO_ROOT / "scripts" / "generate_lightbox_public_status.py"


def _module():
    spec = importlib.util.spec_from_file_location(
        "generate_lightbox_public_status", SCRIPT
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_current_status_preserves_doctrine_and_refuses_universal_claim() -> None:
    generator = _module()
    status = generator.build_status(
        generator._load(generator.MANIFEST_PATH),
        generator._load(generator.REGISTER_PATH),
        generator._load(generator.ASSESSMENT_PATH),
        generator._load(generator.MATRIX_PATH),
    )
    assert generator.validate_status(status) == []
    assert status["doctrine_text_changed"] is False
    assert status["universal_current_conformance_supported"] is False
    assert status["publication_disposition"] == "local_unreleased_status"
    assert status["summary"]["canonical_calculations"] == 1210
    assert status["summary"]["unresolved"] == 1195
    claims = {row["claim"]: row["status"] for row in status["claim_dispositions"]}
    assert claims["Every Calculation is Benchmarked."] == "unsupported"


def test_generated_status_is_current_and_deterministic() -> None:
    generator = _module()
    status = generator.build_status(
        generator._load(generator.MANIFEST_PATH),
        generator._load(generator.REGISTER_PATH),
        generator._load(generator.ASSESSMENT_PATH),
        generator._load(generator.MATRIX_PATH),
    )
    assert generator.JSON_PATH.read_text(encoding="utf-8") == generator.render_json(
        status
    )
    assert generator.MARKDOWN_PATH.read_text(
        encoding="utf-8"
    ) == generator.render_markdown(status)
    assert json.loads(generator.render_json(status)) == status
