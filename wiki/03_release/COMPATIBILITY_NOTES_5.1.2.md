# Compatibility Notes - Moira 5.1.2

Date: 2026-07-22

Moira 5.1.2 is API-compatible with 5.1.1. Public Python signatures, result
vessels, exports, defaults, and REST request/response schemas are unchanged.

## Corrected output

This patch intentionally changes results where the earlier eclipse geometry or
topology was wrong:

- lunar searches now include the 1922-03-13 and 1940-03-23 penumbral events;
- 1988-03-03 is now penumbral rather than partial; and
- affected 2027-2031 solar footprints now return lawful closed penumbral
  components instead of malformed horizon junctions or an incidence-count
  exception.

Applications that persisted eclipse catalogs or cached footprint details
should regenerate the affected records after upgrading.

## Preserved boundaries

- Global lunar greatest eclipse, classification, and contacts use the physical
  geocentric Moon at the event TT epoch.
- Observer-facing lunar visibility geometry may still use reception-time
  apparent vectors where that separately named product requires them.
- Exact cone/disk geometry remains the lunar classifier; the two-degree
  latitude neighborhood is candidate discovery only.
- Python owns solar-footprint doctrine, topology, result assembly, and fallback.
  The new C++ helpers are an internal additive substrate and do not change the
  public interface.
- No NumPy dependency has been added to the base engine, optional runtime, or
  native binding contract.
- The NASA century fixture is validation evidence only and is never consulted
  by runtime eclipse computation.

## Upgrade action

Upgrade to the published `moira-astro==5.1.2` wheel and restart services that
import Moira so every process loads the corrected Python and native paths.
No caller-side flag or request migration is required.
