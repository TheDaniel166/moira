"""Cross-platform guarantees for the website documentation manifest."""

from __future__ import annotations

from scripts.build_website_docs_bundle import (
    _canonical_text_bytes,
    _sha256_path,
)


def test_publication_receipts_normalize_checkout_line_endings(tmp_path) -> None:
    lf_path = tmp_path / "lf.md"
    crlf_path = tmp_path / "crlf.md"
    lf_path.write_bytes(b"# Receipt\n\nPortable text.\n")
    crlf_path.write_bytes(b"# Receipt\r\n\r\nPortable text.\r\n")

    expected = b"# Receipt\n\nPortable text.\n"
    assert _canonical_text_bytes(lf_path) == expected
    assert _canonical_text_bytes(crlf_path) == expected
    assert len(_canonical_text_bytes(lf_path)) == len(_canonical_text_bytes(crlf_path))
    assert _sha256_path(lf_path) == _sha256_path(crlf_path)
