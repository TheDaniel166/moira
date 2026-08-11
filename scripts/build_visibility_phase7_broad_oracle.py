"""Build the source-owned Phase 7 broad physical-event oracle golden.

This offline builder delegates all scientific derivation to the independent
validator module.  It imports neither Moira nor its event solver and performs
no network access.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import validate_visibility_phase7_broad_oracle as oracle


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, default=oracle.DEFAULT_SPEC)
    parser.add_argument(
        "--phase3-golden",
        type=Path,
        default=oracle.DEFAULT_PHASE3_GOLDEN,
    )
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--hipparcos-query", type=Path, required=True)
    parser.add_argument("--hipparcos-readme", type=Path, required=True)
    parser.add_argument(
        "--engine-receipt",
        action="append",
        required=True,
        type=Path,
        dest="engine_receipts",
    )
    parser.add_argument("--output", type=Path, default=oracle.DEFAULT_GOLDEN)
    parser.add_argument(
        "--replace",
        action="store_true",
        help="replace an existing golden intentionally",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    output = arguments.output.resolve()
    if output.exists() and not arguments.replace:
        raise FileExistsError(
            f"refusing to replace existing golden without --replace: {output}"
        )
    derived = oracle.derive(
        spec_path=arguments.spec.resolve(),
        phase3_golden_path=arguments.phase3_golden.resolve(),
        pack_path=arguments.pack.resolve(),
        source_manifest_path=arguments.source_manifest.resolve(),
        source_root=arguments.source_root.resolve(),
        hipparcos_query=arguments.hipparcos_query.resolve(),
        hipparcos_readme=arguments.hipparcos_readme.resolve(),
        engine_receipt_paths=tuple(
            path.resolve() for path in arguments.engine_receipts
        ),
    )
    payload = (
        json.dumps(derived, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(payload)
    print(
        json.dumps(
            {
                "status": "written",
                "output": str(output),
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "case_count": len(derived["cases"]),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
