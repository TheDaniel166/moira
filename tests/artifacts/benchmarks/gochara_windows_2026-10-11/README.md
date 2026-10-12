# Gochar window performance receipts

Produced by `scripts/benchmark_gochara_windows.py` with project Python 3.14.3,
DE441, final request cache ownership and full-interval event bracket evidence.
Four matrix processes ran concurrently, alongside intermittent validation work.
These are measurements of a contended host, not latency or throughput promises.

The four regular JSON files each contain cold/warm 1-, 30-, and 366-day results,
all seven participants, one named ayanamsa and the declared BAV choice. The
Raman file adds two near-station cases retaining unresolved width. Warm calls
reuse the process/serving reader but create new request-owned caches. Windows
peak working set is cumulative per process and includes mapped kernel pages;
it is not Python-only memory and cannot simply be added across processes.

Work units, cache occupancy/hits/misses, event/region counts, complete canonical
JSON bytes and independent coverage fields are retained for each request.
Performance does not establish astronomical or predictive accuracy. See
`wiki/03_validation/GOCHARA_WINDOWS_VALIDATION_2026-10-11.md` for acceptance,
thresholds and interpretation.
