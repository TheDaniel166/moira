# Compatibility Notes — Moira 2.0.0

Date: 2026-04-10

This document covers every caller-visible change in 2.0.0.
Read this if you are upgrading from 1.x.

---

## Four things that may break your code

### 1. Naïve `datetime` objects now raise

**Affected call site:** `jd_from_datetime()`  
**Affected callers:** anyone passing a `datetime` without `tzinfo`

Previously a naïve `datetime` (no `tzinfo`) was silently treated as UTC.
That was a silent assumption and a latent source of wrong output.

It now raises:
```
ValueError: jd_from_datetime requires a timezone-aware datetime;
pass an explicit tzinfo instead of relying on an implicit UTC assumption.
```

**What to do:**

Add `tzinfo=timezone.utc` everywhere you construct a `datetime` for Moira.

```python
from datetime import datetime, timezone

# before (1.x — silently assumed UTC)
jd = jd_from_datetime(datetime(2000, 1, 1, 12, 0, 0))

# after (2.0.0 — explicit)
jd = jd_from_datetime(datetime(2000, 1, 1, 12, 0, 0, tzinfo=timezone.utc))
```

If you use a local time, pass the appropriate tzinfo:

```python
import zoneinfo
dt = datetime(2000, 1, 1, 12, 0, 0, tzinfo=zoneinfo.ZoneInfo("America/New_York"))
jd = jd_from_datetime(dt)
```

---

### 2. `classify_house_system()` raises on unknown codes

**Affected call site:** `classify_house_system(code)`

```
ValueError: unknown house system code 'XX'
```

**What to do:**

Pass only valid `HouseSystem` constants. If you need to guard against unknown
input at a system boundary, wrap in a `try/except ValueError`.

```python
from moira.houses import classify_house_system, HouseSystem

# before (1.x — undefined/fallback behavior)
result = classify_house_system("XX")

# after — guard it if the code comes from external input
try:
    result = classify_house_system(user_provided_code)
except ValueError:
    result = classify_house_system(HouseSystem.PLACIDUS)
```

---

### 3. Strict house policy raises on unknown codes

**Affected call site:** `calculate_houses(..., policy=HousePolicy.strict())` or
any call that explicitly sets `unknown_system=UnknownSystemPolicy.RAISE`

**Default policy is unchanged.** If you use the default `HousePolicy`, nothing
breaks. This only matters if you explicitly request strict behavior.

```python
# raises in 2.0.0 when using strict policy
from moira.houses import calculate_houses, HousePolicy

cusps = calculate_houses(jd, lat, lon, "XX", policy=HousePolicy.strict())
```

**What to do:** Either validate the system code before calling, or catch the
`ValueError` at the boundary where external codes enter.

---

### 4. `decan_at()` no longer accepts `reader`

**Affected call site:** `decan_at(jd, lat, lon, reader=...)`

The optional `reader` parameter has been removed entirely. Passing it now raises
`TypeError: decan_at() got an unexpected keyword argument 'reader'`.

**What to do:**

Remove the `reader` argument. The function is self-contained.

```python
# before (1.x)
result = decan_at(jd, lat, lon, reader=my_reader)

# after (2.0.0)
result = decan_at(jd, lat, lon)
```

---

## Changes that require no action

These changes improve behavior but will not break existing callers.

| Change | What it means for you |
|--------|----------------------|
| House cusps now expose `fallback`, `fallback_reason`, `effective_system` fields | New fields you can optionally inspect. No existing field removed. |
| 50 public policy dataclasses are now immutable and hashable | You can now safely use them as dict keys or in sets. |
| `DecanHoursNight` validates night geometry at construction | If you construct this yourself with invalid data, you will now get a `ValueError` instead of a corrupt result. |
| Heliacal stellar rising corrected for small-arcus-visionis stars | Rising dates for stars like Regulus may shift by one day compared to 1.x. The 2.0.0 result is correct. |

---

## Quick checklist for upgrading

1. Search your codebase for `datetime(` — add `tzinfo=timezone.utc` to any naïve datetime passed to Moira.
2. Search for `jd_from_datetime(` — verify all call sites pass aware datetimes.
3. Search for `classify_house_system(` — verify inputs are always valid `HouseSystem` constants or are guarded.
4. Search for `decan_at(` — remove any `reader=` argument.
5. If you use `HousePolicy.strict()` explicitly, audit those call sites for unknown-code inputs.
