# Machine Contract: Dual-Substrate Backend Architecture

**Status**: Active / Baseline established
**Context**: Moira v3.0.0+
**Goal**: Integrate high-performance C++ kernels without sacrificing the "Light Box Doctrine" of readable, auditable Python reference code.

---

## 1. The Dual-Substrate Law

Moira shall maintain a **Reference Implementation** in pure, readable Python for every astronomical calculation. This is the "Source of Truth." An **Accelerated Implementation** (Native C++) may be provided as an alternative backend, but it must prove its parity against the Reference.

## 2. Backend Definitions

```python
from enum import Enum

class MoiraBackend(Enum):
    PYTHON = "python"  # Canonical Reference (Default)
    NATIVE = "native"  # Accelerated C++ Extension
```

## 3. The Dispatcher Layer (`moira.dispatch`)

The dispatch layer is responsible for routing calls to the appropriate substrate. It must be transparent to the end-user.

### 3.1 Global Configuration
A global settings object governs the default backend, which can be overridden via environment variables or runtime context.

```python
# moira/settings.py
DEFAULT_BACKEND = MoiraBackend.PYTHON
if os.environ.get("MOIRA_ACCELERATE") == "1":
    DEFAULT_BACKEND = MoiraBackend.NATIVE
```

### 3.2 The Decorator Pattern
We use a dispatcher decorator to handle the routing logic at the module level.

```python
# moira/dispatch.py
def accelerate(pillar_name):
    def decorator(func):
        def wrapper(*args, **kwargs):
            if settings.current_backend() == MoiraBackend.NATIVE:
                try:
                    # Attempt to delegate to the native extension
                    native_func = getattr(moira_native, pillar_name)
                    return native_func(*args, **kwargs)
                except (ImportError, AttributeError):
                    # Fallback to Python if native is unavailable
                    return func(*args, **kwargs)
            return func(*args, **kwargs)
        return wrapper
    return decorator
```

## 4. Pillar Integration

Each computationally heavy pillar (Nutation, Orbit, Ephemeris) will be wrapped in the dispatcher.

```python
# moira/nutation.py
@accelerate("nutation")
def calculate_nutation(jd_tdb):
    # Reference Python Implementation (The Truth)
    ...
```

## 5. The Rituals of Validation

To ensure the C++ substrate remains faithful to the celestial truth and justified in its existence, it must pass two separate audits.

### 5.1 The Parity Rite (Accuracy)

1.  **Input Sampling**: Generate 1,000 random Julian Days across the DE441 range (-13200 to +17191).
2.  **Cross-Verification**: Compute the result using both `MoiraBackend.PYTHON` and `MoiraBackend.NATIVE`.
3.  **Threshold Audit**: The results must match within a defined epsilon (e.g., $10^{-12}$ degrees). Any divergence beyond the epsilon is a violation of the contract.

### 5.2 The Performance Mandate (Efficiency)

The C++ layer must not only be correct; it must be "fire." If the native backend does not meet the following minimum acceleration thresholds, it remains a speculative experiment and shall not be merged into the canonical main branch:

- **Bulk Ephemeris Interpolation**: >= 5x speedup over Python.
- **Search Solvers (Stations/Ingresses/Eclipses)**: >= 10x speedup over Python.
- **Harmogram Trace Synthesis**: >= 10x speedup over Python.

These benchmarks shall be measured against the reference implementation on identical hardware under standard load. Complexity without significant acceleration is considered "ceremony without fire" and is architecturally prohibited.

## 6. Implementation Stages (External Workspace)

1.  **Stage 1: Core Math Bridge**: Port `moira/coordinates.py` and `moira/julian.py` (Julian Day, RA/Dec to Ecliptic).
2.  **Stage 2: The Kernel Reader**: Implement the `daf_reader` and `spk_interpolator` in C++ for high-speed ephemeris access.
3.  **Stage 3: Search Solvers**: Port the eclipse and station search algorithms (the primary beneficiaries of speed).

---

## 7. Native Status Matrix

Status date: 2026-05-08

This matrix records the current implementation state of the native backend as it exists in code and checked-in benchmark artifacts. It distinguishes native existence from dispatcher routing and from high-level engine adoption.

| Subsystem | Native implementation exists | Integrated into Python engine | Parity-tested | Benchmarked | Production-routed | Current reading |
| --- | --- | --- | --- | --- | --- | --- |
| Import/build foundation (`_moira_native`, shim, CMake) | Yes | Yes | Yes | No | Yes | Built and resolved through `moira/moira_native.py`; verified by import-resolution tests. |
| Dispatcher framework (`moira.dispatch`) | Yes | Yes | Yes | No | Partial | Real routing layer exists, but only a narrow slice currently uses it. |
| Julian Day / calendar conversion | Yes | Yes | Yes | No | Yes | Live `@accelerate` routing in `moira/julian.py`; parity covered by `tests/test_native_parity.py`. |
| Sidereal time primitives (`earth_rotation_angle`, `greenwich_mean_sidereal_time`, `apparent_sidereal_time`) | Yes | Yes | Yes | Yes | Yes | Live dispatch-routed slice; aggregate checked benchmark shows about `6.14x` median speedup. |
| Geometry / interpolation / solver primitives | Yes | Partial | Partial | Partial | No | Exposed from the extension and used by tests and scripts, but not broadly routed through public engine surfaces. |
| Native DAF catalog reading | Yes | Yes | Yes | Yes | Yes | Used by `moira/spk_reader.py` when available; parity and live-kernel tests exist; measured catalog gain is modest. |
| Native planetary SPK payload extraction | Yes | Yes | Yes | Yes | Yes | Reader ownership advanced into native code for supported type-2/type-3 segments. |
| Native planetary segment evaluation | Yes | Yes | Yes | Yes | Yes | Functionally integrated in `SpkReader`, but the checked artifact still shows a performance regression of about `0.27x` to `0.29x` versus the prior path. |
| Native small-body reader ownership | Yes | Yes | Yes | Yes | Yes | Small-body kernels now run through native-owned reader logic; validation is present; performance baseline is still incomplete. |
| Persistent evaluator classes (`ChebyshevEvaluator`, `RelativeEvaluator`, `TopocentricEvaluator`) | Yes | Partial | Partial | Script-only | No | Present in bindings and benchmark/audit scripts, but not yet a normal high-level engine route. |
| Search pool / native event search primitives | Yes | Partial | Partial | Script-only | No | `SearchPool`, station, ingress, and occultation primitives exist in the extension, but engine-wide adoption remains limited. |
| Native eclipse discovery (`find_solar_eclipses`, `find_lunar_eclipses`) | Yes | Partial | Partial | Script-only | No | Kernels exist in bindings, but `moira/eclipse.py` still remains primarily Python-orchestrated rather than native-dispatched. |
| Cartography helpers | Yes | Partial | Partial | No | No | Native cartography functions are present in bindings, but the repository is in flux around the Python cartography surfaces. |
| Harmogram-native acceleration | No clear evidence | No | No | No | No | The architecture target exists, but this repository does not yet show a validated native harmogram path. |

### 7.1 Present Conclusion

The native backend is past the speculative stub stage. It is strongest today in:

- build/import foundation
- dispatch-routed Julian and sidereal functions
- native SPK/DAF reader ownership
- validated small-body and planetary reader integration

It is weaker in:

- broad high-level engine routing
- stable performance wins for the full planetary native segment path
- evidence-backed adoption of native search and eclipse products into the public Python engine

The practical reading is therefore:

- the forge is real
- the reader substrate is materially advanced
- the high-level event engine is still predominantly Python-governed
- benchmark and tracker claims must be read against the checked artifact set, not against intended phase language alone

## 8. Uranian Doctrine Alignment

By adopting this architecture, we fulfill the Law of Visibility and the Law of Speed simultaneously. We do not bury the math in the machine; we simply build a faster machine to mirror the math.
