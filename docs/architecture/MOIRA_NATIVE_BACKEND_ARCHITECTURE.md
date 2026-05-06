# Machine Contract: Dual-Substrate Backend Architecture

**Status**: Draft / Speculative
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

## 5. The Parity Rite (Validation Strategy)

To ensure the C++ substrate remains faithful to the celestial truth, we implement a **Sovereign Parity Test**.

1.  **Input Sampling**: Generate 1,000 random Julian Days across the DE441 range (-13200 to +17191).
2.  **Cross-Verification**: Compute the result using both `MoiraBackend.PYTHON` and `MoiraBackend.NATIVE`.
3.  **Threshold Audit**: The results must match within a defined epsilon (e.g., $10^{-12}$ degrees). Any divergence beyond the epsilon is a violation of the contract.

## 6. Implementation Stages (External Workspace)

1.  **Stage 1: Core Math Bridge**: Port `moira/coordinates.py` and `moira/julian.py` (Julian Day, RA/Dec to Ecliptic).
2.  **Stage 2: The Kernel Reader**: Implement the `daf_reader` and `spk_interpolator` in C++ for high-speed ephemeris access.
3.  **Stage 3: Search Solvers**: Port the eclipse and station search algorithms (the primary beneficiaries of speed).

---

## 7. Uranian Doctrine Alignment

By adopting this architecture, we fulfill the Law of Visibility and the Law of Speed simultaneously. We do not bury the math in the machine; we simply build a faster machine to mirror the math.
