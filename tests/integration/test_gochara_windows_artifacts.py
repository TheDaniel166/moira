"""Check retained primary evidence integrity; do not regenerate expectations."""
from hashlib import sha256
import json
from pathlib import Path

from moira.gochara import GOCHARA_PLANETS
from moira.sidereal import Ayanamsa


def test_retained_primary_matrix_is_complete_and_raw_responses_are_intact():
    tests=Path(__file__).parents[1]
    spec_path=tests/"fixtures/gochara_windows_validation_spec.json"
    spec=json.loads(spec_path.read_text())
    source=tests/"artifacts/oracle/gochara_windows_2026-10-11"
    batches={}
    for name,count in (("matrix",84),("retrograde",15),("wrap",2)):
        root=source/name
        receipt=json.loads((root/"receipt.json").read_text())
        assert receipt["status"]=="passed" and receipt["external_requested"] is True
        assert receipt["spec_sha256"]==sha256(spec_path.read_bytes()).hexdigest()
        rows=receipt["results"]
        assert len(rows)==count
        requests=json.loads((root/"requests.json").read_text())
        assert len(requests)==count
        for query in requests:
            raw=(root/query["file"]).read_text(encoding="utf-8")
            assert sha256(raw.encode()).hexdigest()==query["sha256"]
        for row in rows:
            assert row["event"]["kind"]=="crossing"
            assert row["horizons"]["angular_error_arcsec"]<=spec["horizons"]["angular_threshold_arcsec"]
            assert row["horizons"]["distance_error_km"]<=spec["horizons"]["distance_threshold_km"]
        batches[name]=rows
    assert {(r["system"],r["planet"]) for r in batches["matrix"]}=={
        (s,p) for s in Ayanamsa.ALL for p in GOCHARA_PLANETS}
    for planet in ("Mercury","Venus","Mars","Jupiter","Saturn"):
        sequence=[r for r in batches["retrograde"] if r["planet"]==planet]
        assert [r["event"]["direction"] for r in sequence]==[1,-1,1]
        assert len({r["event"]["boundary_degrees"] for r in sequence})==1
    assert {r["planet"] for r in batches["wrap"]}=={"Sun","Moon"}
    assert all(r["event"]["boundary_degrees"]==0 for r in batches["wrap"])
