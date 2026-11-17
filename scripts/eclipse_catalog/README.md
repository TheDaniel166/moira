# Provisional eclipse catalog validation tools

These scripts support auditable, resumable **native Moira research runs** and a
separate NASA-compatible lunar run. They do not exactly reproduce NASA's
ephemeris and model, establish physical truth, or certify that
all eclipses or contact branches were found, or admit an event-wide solar path
or catalog-width product. The underlying diagnostics may remain unresolved.
Keep generated data outside the source checkout; never overwrite prior runs.

Use the project virtual environment, set `MOIRA_NO_DOWNLOAD=1`, and supply a
verified planetary-kernel SHA-256. Each run pins its numerical source, native
extension and data, validates source and kernel fingerprints, and records its
own provisional provenance. Rebuild the native extension before running if
its source changed. Freeze source, kernels, and runner scripts for the whole
run; a change requires a new run and new discovery receipts.

1. Run `discovery.py --family solar|lunar --directory OUT --kernel-sha256 HASH`
   for each family. It searches overlapping partitions and writes a discovery
   index and receipt after checking chronology and unique lunations. Existing
   chunks can be resumed with the same parameters, source, and kernel. The
   default half-open TT range spans astronomical years -1999 through 3000.
   The internal search remains subject to the native model and solver limits.
2. For solar circumstances, run `solar_shard.py --index DISCOVERY.csv
   --index-receipt RECEIPT.json --directory SHARDS --output SOLAR.csv
   --kernel-sha256 HASH`. Its workers recompute legacy native quantities and
   preserve field-level statuses. The width is the admitted instantaneous
   support span, not a swept or NASA catalog width. Scientific errors fail the
   run rather than disappearing in a merge.
3. For lunar circumstances, run `lunar_detail.py` with the corresponding
   index and receipt, choosing a unique `--output` for each `--shard-index`
   and a shared `--shard-count`. `--resume` retries failed rows under matching
   metadata. Merge all completed shards with `merge_lunar_detail.py`, passing
   every shard via a separate `--shard` argument. Missing native-solver phases
   and contacts do not prove physical absence; reported signed margins use the
   native greatest-axis epoch.
4. `solar_supplement.py` can inspect a completed, receipted solar detail file
   for path-wide hybrid **evidence** and instantaneous cap **candidates**.
   Its unresolved and incomplete flags are part of the product. It does not
   produce a certified swept boundary or a source-defined catalog width.
5. `lunar_candidate_supplement.py` inspects the native-discovered lunations
   under the opt-in angular and finite-cone shadow policies. Run independent
   shards and use `merge_lunar_candidate_supplement.py` for verified merging.
   A candidate type, contact or non-detection is not certified complete;
   non-detections and unsupported windows are unresolved. NASA-only lunations
   are outside this input and must not be reported as absent eclipses.
6. `compare.py` joins discovery and, optionally, receipted detail with explicit
   pre-change and external inputs. It retains union identities and states
   whether detail was supplied. Supply a solar supplement with `--supplement`
   and `--supplement-receipt`, or lunar candidate outputs with paired
   `--lunar-candidate-supplement` and `--lunar-candidate-receipt` arguments.
   Reference catalogs may use different ephemerides, time scales, radii, and
   event definitions; the comparison is not a general accuracy bound.
7. For the separately labeled lunar `nasa_compat` policy, run
   `canon_discovery.py --directory OUT --kernel-sha256 HASH --jobs 8`. This
   independently searches the full range rather than filtering the native
   event index. It uses the default apparent-Sun/Moon canon method, DE441 and
   NASA's month-midpoint Delta-T convention, while retaining Moira's full-moon
   and eclipse-season gates. It does not prove discovery completeness or
   reproduce NASA's ephemeris. Each chunk and its content checksum can be
   resumed only under the same source, runner, kernel, and partition bounds.
   Run `canon_lunar_detail.py` with that discovery index and receipt, a unique
   `--output` for each `--shard-index`, and a shared `--shard-count`; merge all
   completed shards with `merge_canon_lunar_detail.py`, passing every shard.
   Add the resulting files and receipts to `compare.py` using its paired
   `--compat-discovery*` and `--compat-detail*` options. These results must not
   be mixed with native rows or labeled as exact NASA predictions. There is no
   equivalent NASA-compatible solar search policy in this implementation.

Each command exposes its required arguments with `--help`. A successful merge
establishes accounting relative to its discovery index, not completeness of
that discovery. Run focused tests and independent scientific checks before
making any stronger claim.
