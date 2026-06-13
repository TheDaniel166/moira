# Uranian Backend Standard

**Subsystem:** `moira/uranian.py`
**Computational Domain:** Uranian / Hamburg School hypothetical body positions
**Status:** Backend standard for Phase 12 REST admission

---

## 1. Scope

This standard governs Moira's current Uranian backend surface:

- `UranianBody`
- `UranianPosition`
- `uranian_at(name, jd_ut)`
- `all_uranian_at(jd_ut)`
- `list_uranian()`

The subsystem computes tropical ecliptic longitudes for the Hamburg School
hypothetical bodies and Transpluto from a fixed mean-motion table. It is a
specialist astrological technique surface. It is not an astronomical body
ephemeris for discovered physical planets.

## 2. Authority And Provenance

The implemented canon named by the module is:

- Alfred Witte, *Regelwerk fur Planetenbilder* (1928)
- Udo Rudolph, *ABC of Uranian Astrology* (2005)
- Landscheidt-style Transpluto mean-motion lineage as embodied in the current
  `_URANIAN_ELEMENTS` table

The backend table is an internal Moira table of linear mean ephemerides:

```text
longitude = (longitude_at_J2000 + daily_motion * (jd_ut - J2000)) mod 360
```

The table is not sourced from JPL, NAIF, IAU, IERS, SOFA, ERFA, or a physical
SPK kernel. That is intentional: these are Hamburg School hypothetical points,
not physical planets.

## 3. Governing Objects

### 3.1 Uranian body name

A Uranian body name is one canonical string in the implemented name registry.

Current admitted names:

| Name | Status |
|---|---|
| `Cupido` | Hamburg School hypothetical body |
| `Hades` | Hamburg School hypothetical body |
| `Zeus` | Hamburg School hypothetical body |
| `Kronos` | Hamburg School hypothetical body |
| `Apollon` | Hamburg School hypothetical body |
| `Admetos` | Hamburg School hypothetical body |
| `Vulkanus` | Hamburg School hypothetical body |
| `Poseidon` | Hamburg School hypothetical body |
| `Transpluto` | hypothetical Transpluto point |

The current backend exposes nine names. Transport documentation must not call
the surface "all eight" unless it is explicitly excluding Transpluto.

### 3.2 Uranian position

A `UranianPosition` is the computed position of one admitted hypothetical body
at one Julian Day UT. It preserves:

- `name`
- tropical ecliptic `longitude` in `[0, 360)`
- zodiac `sign`
- `sign_symbol`
- `sign_degree`
- constant mean daily `speed`

The sign fields are derived by `moira.constants.sign_of(longitude)`.

## 4. Admitted Computations

### 4.1 Single-body position

`uranian_at(name, jd_ut)` computes one admitted body by exact table lookup.

Current behavior:

- body names are case-sensitive
- unknown names raise `KeyError`
- the caller is responsible for supplying a finite Julian Day
- no kernel, database, or observer location is used

### 4.2 Bulk position set

`all_uranian_at(jd_ut)` computes the full current table in canonical table
order.

### 4.3 Name catalogue

`list_uranian()` returns the implemented name set in canonical table order.

## 5. Required Transport Invariants

Any REST admission for `/v1/uranian/*` must preserve these invariants:

- reject non-finite `jd_ut` before calling the engine
- reject unknown body names with a clear client error
- preserve case-sensitive canonical names in responses
- label every response as `hypothetical_body`, not `planet`
- expose `model = "linear_mean_motion_table"`
- expose `frame = "tropical_ecliptic_longitude"`
- expose `epoch = "J2000"`
- expose the body set version or provenance note in catalogue responses
- keep single-position and bulk-position routes separate
- keep chart profiles, midpoint trees, cosmobiology networks, and
  interpretation out of the first admission

Transport must not silently substitute a physical body, asteroid, TNO,
fictional planet, or SPK kernel object for a Uranian name.

## 6. Validation Requirements

Minimum validation for transport admission:

```powershell
.\.venv\Scripts\python.exe -m py_compile moira\uranian.py
.\.venv\Scripts\python.exe -m pytest tests\unit -q -k uranian
```

If no focused Uranian tests exist at admission time, the transport work must
add server tests covering:

- catalogue returns exactly the admitted name set
- single-body position returns longitude in `[0, 360)`
- bulk response returns all admitted names in deterministic order
- unknown body names fail clearly
- non-finite `jd_ut` fails before engine invocation
- provenance identifies the bodies as hypothetical Hamburg School points

## 7. Non-Goals

This subsystem does not provide:

- physical-planet ephemerides
- JPL/NAIF-backed body states
- discovered trans-Neptunian object positions
- fixed-star or asteroid positions
- midpoint trees
- Uranian dial/aspect interpretation
- cosmobiology network analysis
- location-dependent or topocentric computation
- sidereal reduction
- velocity models beyond the constant mean daily speed in the table

Those products require separate backend standards and route-admission packets.

## 8. Change Policy

The following are doctrine-sensitive and require explicit review before change:

- the admitted body name set
- any `_URANIAN_ELEMENTS` longitude or daily-motion value
- whether Transpluto is included in bulk output
- any claim that the bodies are physical astronomical objects
- any switch from linear mean-motion table computation to another model

The REST layer may wrap and validate the current backend. It must not redefine
the Uranian model.
