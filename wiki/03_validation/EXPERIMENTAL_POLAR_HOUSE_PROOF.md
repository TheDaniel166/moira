# Experimental Polar House Proof Register

Status: reproducible experiment register

Purpose
-------
This page is for direct reproduction.

Each entry below is meant to be read like this:

> Here is the date, time, place, and house system.
> Run that chart.
> If the experimental implementation is working, you should get these house cusps.

That is the whole purpose of this document.

How to use this page
--------------------

For each experiment below:

1. use the exact date and time shown
2. use the exact latitude and longitude shown
3. use the exact house system shown
4. use `HousePolicy.experimental()`
5. compare your returned 12 house cusps to the expected 12 cusps listed here

If the result matches, the experiment passed.

Authoritative runtime
---------------------

All experiments on this page were checked in:

```powershell
.venv\Scripts\python.exe
```

Public engine command template
------------------------------

```powershell
@'
from datetime import datetime, timezone
from moira.constants import HouseSystem
from moira.houses import calculate_houses, HousePolicy
from moira.julian import jd_from_datetime

dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
jd = jd_from_datetime(dt)

h = calculate_houses(
    jd,
    77.0,
    169.54292771060392,
    HouseSystem.PLACIDUS,
    policy=HousePolicy.experimental(),
)

print("effective_system =", h.effective_system)
print("fallback =", h.fallback)
for i, cusp in enumerate(h.cusps, start=1):
    print(f"H{i:02d} = {cusp:.12f}")
'@ | .venv\Scripts\python.exe -
```

Admitted systems
----------------

This page currently contains reproducible experiments for:

- Placidus
- Koch
- Regiomontanus
- Topocentric
- Campanus
- Alcabitius

Validation status
-----------------

| System | Experimental live | Ordered latitudes | Practical latitudes | Stable latitudes | Dominant failure mode | Promotion readiness |
| --- | --- | --- | --- | --- | --- | --- |
| `Placidus` | yes | `217 / 468` | `217 / 468` | `14 / 468` | missing required roots | already integrated |
| `Koch` | yes | `468 / 468` | `256 / 468` | `64 / 468` | unordered cusp cycle | not yet |
| `Regiomontanus` | yes | `468 / 468` | `298 / 468` | `162 / 468` | no valid ordered figure / practical collapse near the pole | candidate after more doctrine work |
| `Topocentric` | yes | `468 / 468` | `342 / 468` | `162 / 468` | unordered cusp cycle | possible later, not first |
| `Campanus` | yes | `468 / 468` | `468 / 468` | `290 / 468` | unordered cusp cycle | stronger candidate |
| `Alcabitius` | yes | `468 / 468` | `468 / 468` | `468 / 468` | rare unordered cusp cycle | strongest promotion candidate |

Current promotion recommendation:

- `Alcabitius` is the best candidate to move out of experimental-only handling first.
- It has the strongest Greenwich 2000 surface, the cleanest taxonomy, zero assembly failures, and the clearest direct governing object.

Current practical-screening doctrine
------------------------------------

The validation corpus now records three distinct layers:

- `ordered`: the cusp cycle stays strictly forward in house order
- `practically admissible`: the ordered cycle also satisfies `rho_max = 7.0`
- `practically stable`: the practical result survives a full `stability_radius = 2` neighborhood

That means a chart can be:

- ordered but still too distorted to count as practical
- practical at one timestamp but too fragile to count as stable

This matters most near the pole. The witness charts below prove that the implementations are real. The sweep artifacts show how much of the polar surface remains merely ordered, how much remains practical, and how much remains stable under the current doctrine.

Part I - Placidus experiments
-----------------------------

### Greenwich year-2000 coverage sweep

This is the broader proof run for experimental Placidus:

- System: `HouseSystem.PLACIDUS`
- Policy: `HousePolicy.experimental()`
- Longitude: `0.0`
- Date range: `2000-01-01 00:00:00 UTC` through `2000-12-31 22:00:00 UTC`
- Time cadence: every `2` hours
- Latitude range: every polar latitude from `-89.9` to `89.9` in `0.1` increments, using the sampled polar-cap band
- Timestamp count: `4392`
- Latitude count: `468`
- Total evaluations: `2055456`

What was successful:

- `217 / 468` sampled latitudes produced some ordered figure
- `217 / 468` sampled latitudes produced some practically admissible figure under `rho_max = 7.0`
- `14 / 468` sampled latitudes produced some practically stable figure under `stability_radius = 2`
- the dominant failure mode remained `NO_REQUIRED_ROOTS`, not ordering failure

Representative success fractions:

| Latitude | Successful charts | Total charts | Success fraction | Practical charts | Stable charts |
| --- | --- | --- | --- | --- | --- |
| `66.6` | `3945` | `4392` | `0.898224043716` | `2080` | `536` |
| `77.0` | `21` | `4392` | `0.004781420765` | `21` | `0` |
| `89.9` | `0` | `4392` | `0.0` | `0` | `0` |

Sweep artifacts:

- [experimental_placidus_greenwich_2000_2h_by_latitude.csv](/C:/Users/nilad/OneDrive/Desktop/Moira%20C++/reports/validation/experimental_placidus_greenwich_2000_2h_by_latitude.csv)
- [experimental_placidus_greenwich_2000_2h_summary.json](/C:/Users/nilad/OneDrive/Desktop/Moira%20C++/reports/validation/experimental_placidus_greenwich_2000_2h_summary.json)
- [experimental_placidus_greenwich_2000_2h_daily_calendar.csv](/C:/Users/nilad/OneDrive/Desktop/Moira%20C++/reports/validation/experimental_placidus_greenwich_2000_2h_daily_calendar.csv)
- [experimental_placidus_greenwich_2000_2h_daily_calendar_summary.json](/C:/Users/nilad/OneDrive/Desktop/Moira%20C++/reports/validation/experimental_placidus_greenwich_2000_2h_daily_calendar_summary.json)

### Experiment P1 - Experimental Placidus

Witness type:

- shared witness
- this same chart is also a valid Koch experiment

Run this chart:

- System: `HouseSystem.PLACIDUS`
- Policy: `HousePolicy.experimental()`
- Date: `2000-01-01`
- Time: `12:00:00 UTC`
- Latitude: `77.0`
- Longitude: `169.54292771060392`

You should get:

- effective system: `P`
- fallback: `False`

Expected houses:

| House | Expected cusp |
| --- | --- |
| H01 | `180.000000000000` |
| H02 | `194.281463173407` |
| H03 | `214.240152504128` |
| H04 | `270.000000000000` |
| H05 | `325.759847495872` |
| H06 | `345.718536826593` |
| H07 | `0.000000000000` |
| H08 | `14.281463173407` |
| H09 | `34.240152504128` |
| H10 | `90.000000000000` |
| H11 | `145.759847495872` |
| H12 | `165.718536826593` |

### Experiment P2 - Experimental Placidus

Witness type:

- system-specific witness
- this chart is recorded here as a Placidus proof chart

Run this chart:

- System: `HouseSystem.PLACIDUS`
- Policy: `HousePolicy.experimental()`
- Date: `2025-05-01`
- Time: `12:00:00 UTC`
- Latitude: `77.0`
- Longitude: `50.0`

You should get:

- effective system: `P`
- fallback: `False`

Expected houses:

| House | Expected cusp |
| --- | --- |
| H01 | `179.875079261148` |
| H02 | `194.129510719138` |
| H03 | `214.180196624749` |
| H04 | `269.697374937284` |
| H05 | `325.708437616338` |
| H06 | `345.567246855225` |
| H07 | `359.875079261148` |
| H08 | `14.129510719138` |
| H09 | `34.180196624749` |
| H10 | `89.697374937284` |
| H11 | `145.708437616338` |
| H12 | `165.567246855225` |

### Experiment P3 - Experimental Placidus

Witness type:

- shared witness
- this same chart is also a valid Koch experiment

Run this chart:

- System: `HouseSystem.PLACIDUS`
- Policy: `HousePolicy.experimental()`
- Date: `2025-09-01`
- Time: `12:00:00 UTC`
- Latitude: `77.0`
- Longitude: `290.0`

You should get:

- effective system: `P`
- fallback: `False`

Expected houses:

| House | Expected cusp |
| --- | --- |
| H01 | `180.343009791728` |
| H02 | `194.696843786223` |
| H03 | `214.366161042946` |
| H04 | `270.830970848494` |
| H05 | `325.936889227409` |
| H06 | `346.135797976120` |
| H07 | `0.343009791728` |
| H08 | `14.696843786223` |
| H09 | `34.366161042946` |
| H10 | `90.830970848493` |
| H11 | `145.936889227409` |
| H12 | `166.135797976120` |

Part II - Koch experiments
--------------------------

### Greenwich year-2000 coverage sweep

This is the broader proof run for experimental Koch:

- System: `HouseSystem.KOCH`
- Policy: `HousePolicy.experimental()`
- Longitude: `0.0`
- Date range: `2000-01-01 00:00:00 UTC` through `2000-12-31 22:00:00 UTC`
- Time cadence: every `2` hours
- Latitude range: every polar latitude from `-89.9` to `89.9` in `0.1` increments, using the sampled polar-cap band
- Timestamp count: `4392`
- Latitude count: `468`
- Total evaluations: `2055456`

What was successful:

- `468 / 468` sampled latitudes produced some ordered figure
- `256 / 468` sampled latitudes produced some practically admissible figure under `rho_max = 7.0`
- `64 / 468` sampled latitudes produced some practically stable figure under `stability_radius = 2`
- failures were dominated by `UNORDERED_CUSP_CYCLE`, not branch-selection or assembly failure

Representative success fractions:

| Latitude | Successful charts | Total charts | Success fraction | Practical charts | Stable charts |
| --- | --- | --- | --- | --- | --- |
| `66.6` | `4243` | `4392` | `0.966074681239` | `2124` | `654` |
| `77.0` | `668` | `4392` | `0.152094717668` | `246` | `0` |
| `89.9` | `6` | `4392` | `0.001366120219` | `0` | `0` |

Sweep artifacts:

- [experimental_koch_greenwich_2000_2h_by_latitude.csv](/C:/Users/nilad/OneDrive/Desktop/Moira%20C++/reports/validation/experimental_koch_greenwich_2000_2h_by_latitude.csv)
- [experimental_koch_greenwich_2000_2h_summary.json](/C:/Users/nilad/OneDrive/Desktop/Moira%20C++/reports/validation/experimental_koch_greenwich_2000_2h_summary.json)
- [experimental_koch_greenwich_2000_2h_daily_calendar.csv](/C:/Users/nilad/OneDrive/Desktop/Moira%20C++/reports/validation/experimental_koch_greenwich_2000_2h_daily_calendar.csv)
- [experimental_koch_greenwich_2000_2h_daily_calendar_summary.json](/C:/Users/nilad/OneDrive/Desktop/Moira%20C++/reports/validation/experimental_koch_greenwich_2000_2h_daily_calendar_summary.json)

### Experiment K1 - Experimental Koch

Witness type:

- shared witness
- this same chart is also a valid Placidus experiment

Run this chart:

- System: `HouseSystem.KOCH`
- Policy: `HousePolicy.experimental()`
- Date: `2000-01-01`
- Time: `12:00:00 UTC`
- Latitude: `77.0`
- Longitude: `169.54292771060392`

You should get:

- effective system: `K`
- fallback: `False`

Expected houses:

| House | Expected cusp |
| --- | --- |
| H01 | `180.000000000000` |
| H02 | `201.651522746749` |
| H03 | `214.414674624403` |
| H04 | `270.000000000000` |
| H05 | `325.585325375597` |
| H06 | `338.348477253251` |
| H07 | `0.000000000000` |
| H08 | `21.651522746749` |
| H09 | `34.414674624403` |
| H10 | `90.000000000000` |
| H11 | `145.585325375597` |
| H12 | `158.348477253251` |

### Experiment K2 - Experimental Koch

Witness type:

- system-specific witness
- this chart is recorded here as a Koch proof chart

Run this chart:

- System: `HouseSystem.KOCH`
- Policy: `HousePolicy.experimental()`
- Date: `2025-05-01`
- Time: `12:00:00 UTC`
- Latitude: `77.0`
- Longitude: `55.0`

You should get:

- effective system: `K`
- fallback: `False`

Expected houses:

| House | Expected cusp |
| --- | --- |
| H01 | `181.768256750332` |
| H02 | `203.135525327552` |
| H03 | `214.403361812087` |
| H04 | `274.286313801183` |
| H05 | `325.807806387214` |
| H06 | `339.878558759098` |
| H07 | `1.768256750332` |
| H08 | `23.135525327552` |
| H09 | `34.403361812087` |
| H10 | `94.286313801183` |
| H11 | `145.807806387214` |
| H12 | `159.878558759098` |

### Experiment K3 - Experimental Koch

Witness type:

- shared witness
- this same chart is also a valid Placidus experiment

Run this chart:

- System: `HouseSystem.KOCH`
- Policy: `HousePolicy.experimental()`
- Date: `2025-09-01`
- Time: `12:00:00 UTC`
- Latitude: `77.0`
- Longitude: `290.0`

You should get:

- effective system: `K`
- fallback: `False`

Expected houses:

| House | Expected cusp |
| --- | --- |
| H01 | `180.343009791728` |
| H02 | `201.942603995302` |
| H03 | `214.430622315864` |
| H04 | `270.830970848494` |
| H05 | `325.612517675549` |
| H06 | `338.642242453556` |
| H07 | `0.343009791728` |
| H08 | `21.942603995302` |
| H09 | `34.430622315864` |
| H10 | `90.830970848493` |
| H11 | `145.612517675549` |
| H12 | `158.642242453556` |

Part III - Regiomontanus experiments
------------------------------------

### Why this section is different

The Placidus and Koch sections above are witness-chart proofs.

This Regiomontanus section does two jobs:

- it records exact charts a user can reproduce
- it records the larger latitude sweep that shows the implementation works far beyond one latitude

### Greenwich year-2000 coverage sweep

This is the broader proof run for experimental Regiomontanus:

- System: `HouseSystem.REGIOMONTANUS`
- Policy: `HousePolicy.experimental()`
- Longitude: `0.0`
- Date range: `2000-01-01 00:00:00 UTC` through `2000-12-31 22:00:00 UTC`
- Time cadence: every `2` hours
- Latitude range: every polar latitude from `-89.9` to `89.9` in `0.1` increments, using the sampled polar-cap band
- Timestamp count: `4392`
- Latitude count: `468`
- Total evaluations: `2055456`

What was successful:

- every sampled polar latitude had at least one ordered experimental Regiomontanus chart
- `468 / 468` sampled latitudes produced some ordered figure
- `298 / 468` sampled latitudes produced some practically admissible figure under `rho_max = 7.0`
- `162 / 468` sampled latitudes produced some practically stable figure under `stability_radius = 2`

Representative success fractions:

| Latitude | Successful charts | Total charts | Success fraction |
| --- | --- | --- | --- |
| `66.6` | `4308` | `4392` | `0.980874316940` |
| `70.0` | `3592` | `4392` | `0.817850637523` |
| `77.0` | `2979` | `4392` | `0.678278688525` |
| `80.0` | `2784` | `4392` | `0.633879781421` |
| `85.0` | `2482` | `4392` | `0.565118397086` |
| `89.9` | `2201` | `4392` | `0.501138433515` |

Sweep artifacts:

- [experimental_regiomontanus_greenwich_2000_2h_by_latitude.csv](/C:/Users/nilad/OneDrive/Desktop/Moira%20C++/reports/validation/experimental_regiomontanus_greenwich_2000_2h_by_latitude.csv)
- [experimental_regiomontanus_greenwich_2000_2h_summary.json](/C:/Users/nilad/OneDrive/Desktop/Moira%20C++/reports/validation/experimental_regiomontanus_greenwich_2000_2h_summary.json)
- [experimental_regiomontanus_greenwich_2000_2h_daily_calendar.csv](/C:/Users/nilad/OneDrive/Desktop/Moira%20C++/reports/validation/experimental_regiomontanus_greenwich_2000_2h_daily_calendar.csv)
- [experimental_regiomontanus_greenwich_2000_2h_daily_calendar_summary.json](/C:/Users/nilad/OneDrive/Desktop/Moira%20C++/reports/validation/experimental_regiomontanus_greenwich_2000_2h_daily_calendar_summary.json)

### Experiment R1 - Experimental Regiomontanus

Witness type:

- coverage witness
- low-edge polar witness from the Greenwich full-year sweep

Run this chart:

- System: `HouseSystem.REGIOMONTANUS`
- Policy: `HousePolicy.experimental()`
- Date: `2000-01-01`
- Time: `00:00:00 UTC`
- Latitude: `66.6`
- Longitude: `0.0`

You should get:

- effective system: `R`
- fallback: `False`

Expected houses:

| House | Expected cusp |
| --- | --- |
| H01 | `185.422680983809` |
| H02 | `203.191770783464` |
| H03 | `230.519362855719` |
| H04 | `279.156665557363` |
| H05 | `323.843615316397` |
| H06 | `348.324626233702` |
| H07 | `5.422680983809` |
| H08 | `23.191770783464` |
| H09 | `50.519362855719` |
| H10 | `99.156665557363` |
| H11 | `143.843615316397` |
| H12 | `168.324626233702` |

### Experiment R2 - Experimental Regiomontanus

Witness type:

- coverage witness
- middle polar witness from the Greenwich full-year sweep

Run this chart:

- System: `HouseSystem.REGIOMONTANUS`
- Policy: `HousePolicy.experimental()`
- Date: `2000-01-01`
- Time: `00:00:00 UTC`
- Latitude: `77.0`
- Longitude: `0.0`

You should get:

- effective system: `R`
- fallback: `False`

Expected houses:

| House | Expected cusp |
| --- | --- |
| H01 | `183.769189611989` |
| H02 | `196.309044833020` |
| H03 | `218.626144638566` |
| H04 | `279.156665557363` |
| H05 | `332.151903075644` |
| H06 | `351.719179610235` |
| H07 | `3.769189611989` |
| H08 | `16.309044833020` |
| H09 | `38.626144638566` |
| H10 | `99.156665557363` |
| H11 | `152.151903075644` |
| H12 | `171.719179610235` |

### Experiment R3 - Experimental Regiomontanus

Witness type:

- coverage witness
- near-pole witness from the Greenwich full-year sweep

Run this chart:

- System: `HouseSystem.REGIOMONTANUS`
- Policy: `HousePolicy.experimental()`
- Date: `2000-01-01`
- Time: `00:00:00 UTC`
- Latitude: `89.9`
- Longitude: `0.0`

You should get:

- effective system: `R`
- fallback: `False`

Expected houses:

| House | Expected cusp |
| --- | --- |
| H01 | `180.043331186262` |
| H02 | `180.185804533130` |
| H03 | `180.471085418668` |
| H04 | `279.156665557363` |
| H05 | `359.616599040921` |
| H06 | `359.900971410093` |
| H07 | `0.043331186262` |
| H08 | `0.185804533130` |
| H09 | `0.471085418668` |
| H10 | `99.156665557363` |
| H11 | `179.616599040921` |
| H12 | `179.900971410093` |

Part IV - Topocentric experiments
---------------------------------

### Greenwich year-2000 coverage sweep

This is the broader proof run for experimental Topocentric:

- System: `HouseSystem.TOPOCENTRIC`
- Policy: `HousePolicy.experimental()`
- Longitude: `0.0`
- Date range: `2000-01-01 00:00:00 UTC` through `2000-12-31 22:00:00 UTC`
- Time cadence: every `2` hours
- Latitude range: every polar latitude from `-89.9` to `89.9` in `0.1` increments, using the sampled polar-cap band
- Timestamp count: `4392`
- Latitude count: `468`
- Total evaluations: `2055456`

What was successful:

- every sampled polar latitude had at least one successful experimental Topocentric chart
- `468 / 468` sampled latitudes produced some valid ordered figure
- `342 / 468` sampled latitudes produced some practically admissible figure under `rho_max = 7.0`
- `162 / 468` sampled latitudes produced some practically stable figure under `stability_radius = 2`
- failures were `UNORDERED_CUSP_CYCLE`, not assembly failures

Representative success fractions:

| Latitude | Successful charts | Total charts | Success fraction |
| --- | --- | --- | --- |
| `66.6` | `3327` | `4392` | `0.757513661202` |
| `77.0` | `2388` | `4392` | `0.543715846995` |
| `89.9` | `1669` | `4392` | `0.380009107468` |

### Experiment T1 - Experimental Topocentric

Witness type:

- coverage witness
- lower polar-band witness from the Greenwich full-year sweep

Run this chart:

- System: `HouseSystem.TOPOCENTRIC`
- Policy: `HousePolicy.experimental()`
- Date: `2000-01-01`
- Time: `00:00:00 UTC`
- Latitude: `66.6`
- Longitude: `0.0`

You should get:

- effective system: `T`
- fallback: `False`

Expected houses:

| House | Expected cusp |
| --- | --- |
| H01 | `185.422680983809` |
| H02 | `206.016381205250` |
| H03 | `236.546906354382` |
| H04 | `279.156665557363` |
| H05 | `319.446511000292` |
| H06 | `346.921172025266` |
| H07 | `5.422680983809` |
| H08 | `26.016381205250` |
| H09 | `56.546906354382` |
| H10 | `99.156665557363` |
| H11 | `139.446511000292` |
| H12 | `166.921172025266` |

### Experiment T2 - Experimental Topocentric

Witness type:

- coverage witness
- middle polar witness from the Greenwich full-year sweep

Run this chart:

- System: `HouseSystem.TOPOCENTRIC`
- Policy: `HousePolicy.experimental()`
- Date: `2000-01-01`
- Time: `00:00:00 UTC`
- Latitude: `77.0`
- Longitude: `0.0`

You should get:

- effective system: `T`
- fallback: `False`

Expected houses:

| House | Expected cusp |
| --- | --- |
| H01 | `183.769189611989` |
| H02 | `199.129688499338` |
| H03 | `226.593516688705` |
| H04 | `279.156665557363` |
| H05 | `326.627676452184` |
| H06 | `350.329358358323` |
| H07 | `3.769189611989` |
| H08 | `19.129688499338` |
| H09 | `46.593516688705` |
| H10 | `99.156665557363` |
| H11 | `146.627676452184` |
| H12 | `170.329358358323` |

### Experiment T3 - Experimental Topocentric

Witness type:

- coverage witness
- near-pole witness from the Greenwich full-year sweep

Run this chart:

- System: `HouseSystem.TOPOCENTRIC`
- Policy: `HousePolicy.experimental()`
- Date: `2000-01-01`
- Time: `00:00:00 UTC`
- Latitude: `89.9`
- Longitude: `0.0`

You should get:

- effective system: `T`
- fallback: `False`

Expected houses:

| House | Expected cusp |
| --- | --- |
| H01 | `180.043331186262` |
| H02 | `180.241110603150` |
| H03 | `180.705637702471` |
| H04 | `279.156665557363` |
| H05 | `359.426384876755` |
| H06 | `359.871525237486` |
| H07 | `0.043331186262` |
| H08 | `0.241110603150` |
| H09 | `0.705637702471` |
| H10 | `99.156665557363` |
| H11 | `179.426384876755` |
| H12 | `179.871525237486` |

Part V - Campanus experiments
-----------------------------

### Greenwich year-2000 coverage sweep

This is the broader proof run for experimental Campanus:

- System: `HouseSystem.CAMPANUS`
- Policy: `HousePolicy.experimental()`
- Longitude: `0.0`
- Date range: `2000-01-01 00:00:00 UTC` through `2000-12-31 22:00:00 UTC`
- Time cadence: every `2` hours
- Latitude range: every polar latitude from `-89.9` to `89.9` in `0.1` increments, using the sampled polar-cap band
- Timestamp count: `4392`
- Latitude count: `468`
- Total evaluations: `2055456`

What was successful:

- every sampled polar latitude had at least one successful experimental Campanus chart
- `468 / 468` sampled latitudes produced some valid ordered figure
- `468 / 468` sampled latitudes produced some practically admissible figure under `rho_max = 7.0`
- `290 / 468` sampled latitudes produced some practically stable figure under `stability_radius = 2`
- failures were `UNORDERED_CUSP_CYCLE`, not branch-selection or assembly failures

Representative success fractions:

| Latitude | Successful charts | Total charts | Success fraction |
| --- | --- | --- | --- |
| `66.6` | `4308` | `4392` | `0.980874316940` |
| `77.0` | `2979` | `4392` | `0.678278688525` |
| `89.9` | `2201` | `4392` | `0.501138433515` |

### Experiment C1 - Experimental Campanus

Witness type:

- coverage witness
- lower polar-band witness from the Greenwich full-year sweep

Run this chart:

- System: `HouseSystem.CAMPANUS`
- Policy: `HousePolicy.experimental()`
- Date: `2000-01-01`
- Time: `00:00:00 UTC`
- Latitude: `66.6`
- Longitude: `0.0`

You should get:

- effective system: `C`
- fallback: `False`

Expected houses:

| House | Expected cusp |
| --- | --- |
| H01 | `185.422680983809` |
| H02 | `225.230044828834` |
| H03 | `255.803255540707` |
| H04 | `279.156665557363` |
| H05 | `301.388371591396` |
| H06 | `328.493210273848` |
| H07 | `5.422680983809` |
| H08 | `45.230044828834` |
| H09 | `75.803255540707` |
| H10 | `99.156665557363` |
| H11 | `121.388371591396` |
| H12 | `148.493210273848` |

### Experiment C2 - Experimental Campanus

Witness type:

- coverage witness
- middle polar witness from the Greenwich full-year sweep

Run this chart:

- System: `HouseSystem.CAMPANUS`
- Policy: `HousePolicy.experimental()`
- Date: `2000-01-01`
- Time: `00:00:00 UTC`
- Latitude: `77.0`
- Longitude: `0.0`

You should get:

- effective system: `C`
- fallback: `False`

Expected houses:

| House | Expected cusp |
| --- | --- |
| H01 | `183.769189611989` |
| H02 | `230.593447963054` |
| H03 | `259.739210989730` |
| H04 | `279.156665557363` |
| H05 | `297.446564645606` |
| H06 | `322.183166416833` |
| H07 | `3.769189611989` |
| H08 | `50.593447963054` |
| H09 | `79.739210989730` |
| H10 | `99.156665557363` |
| H11 | `117.446564645606` |
| H12 | `142.183166416833` |

### Experiment C3 - Experimental Campanus

Witness type:

- coverage witness
- near-pole witness from the Greenwich full-year sweep

Run this chart:

- System: `HouseSystem.CAMPANUS`
- Policy: `HousePolicy.experimental()`
- Date: `2000-01-01`
- Time: `00:00:00 UTC`
- Latitude: `89.9`
- Longitude: `0.0`

You should get:

- effective system: `C`
- fallback: `False`

Expected houses:

| House | Expected cusp |
| --- | --- |
| H01 | `180.043331186262` |
| H02 | `241.596663353028` |
| H03 | `265.831566365174` |
| H04 | `279.156665557363` |
| H05 | `291.570947659290` |
| H06 | `310.823617351052` |
| H07 | `0.043331186262` |
| H08 | `61.596663353028` |
| H09 | `85.831566365174` |
| H10 | `99.156665557363` |
| H11 | `111.570947659290` |
| H12 | `130.823617351052` |

Part VI - Alcabitius experiments
--------------------------------

### Greenwich year-2000 coverage sweep

This is the broader proof run for experimental Alcabitius:

- System: `HouseSystem.ALCABITIUS`
- Policy: `HousePolicy.experimental()`
- Longitude: `0.0`
- Date range: `2000-01-01 00:00:00 UTC` through `2000-12-31 22:00:00 UTC`
- Time cadence: every `2` hours
- Latitude range: every polar latitude from `-89.9` to `89.9` in `0.1` increments, using the sampled polar-cap band
- Timestamp count: `4392`
- Latitude count: `468`
- Total evaluations: `2055456`

What was successful:

- every sampled polar latitude had at least one successful experimental Alcabitius chart
- `468 / 468` sampled latitudes produced some valid ordered figure
- `468 / 468` sampled latitudes produced some practically admissible figure under `rho_max = 7.0`
- `468 / 468` sampled latitudes produced some practically stable figure under `stability_radius = 2`
- failures were rare `UNORDERED_CUSP_CYCLE` cases, not assembly failures

Representative success fractions:

| Latitude | Successful charts | Total charts | Success fraction |
| --- | --- | --- | --- |
| `66.6` | `4386` | `4392` | `0.998633879781` |
| `77.0` | `4333` | `4392` | `0.986566484517` |
| `89.9` | `4391` | `4392` | `0.999772313297` |

### Experiment A1 - Experimental Alcabitius

Witness type:

- coverage witness
- lower polar-band witness from the Greenwich full-year sweep

Run this chart:

- System: `HouseSystem.ALCABITIUS`
- Policy: `HousePolicy.experimental()`
- Date: `2000-01-01`
- Time: `00:00:00 UTC`
- Latitude: `66.6`
- Longitude: `0.0`

You should get:

- effective system: `B`
- fallback: `False`

Expected houses:

| House | Expected cusp |
| --- | --- |
| H01 | `185.422680983809` |
| H02 | `219.029154047627` |
| H03 | `249.944020921531` |
| H04 | `279.156665557363` |
| H05 | `305.928797557541` |
| H06 | `334.791105091424` |
| H07 | `5.422680983809` |
| H08 | `39.029154047627` |
| H09 | `69.944020921531` |
| H10 | `99.156665557363` |
| H11 | `125.928797557541` |
| H12 | `154.791105091424` |

### Experiment A2 - Experimental Alcabitius

Witness type:

- coverage witness
- middle polar witness from the Greenwich full-year sweep

Run this chart:

- System: `HouseSystem.ALCABITIUS`
- Policy: `HousePolicy.experimental()`
- Date: `2000-01-01`
- Time: `00:00:00 UTC`
- Latitude: `77.0`
- Longitude: `0.0`

You should get:

- effective system: `B`
- fallback: `False`

Expected houses:

| House | Expected cusp |
| --- | --- |
| H01 | `183.769189611989` |
| H02 | `217.993380660366` |
| H03 | `249.469077701176` |
| H04 | `279.156665557363` |
| H05 | `305.434657698176` |
| H06 | `333.720583982106` |
| H07 | `3.769189611989` |
| H08 | `37.993380660366` |
| H09 | `69.469077701176` |
| H10 | `99.156665557363` |
| H11 | `125.434657698176` |
| H12 | `153.720583982106` |

### Experiment A3 - Experimental Alcabitius

Witness type:

- coverage witness
- near-pole witness from the Greenwich full-year sweep

Run this chart:

- System: `HouseSystem.ALCABITIUS`
- Policy: `HousePolicy.experimental()`
- Date: `2000-01-01`
- Time: `00:00:00 UTC`
- Latitude: `89.9`
- Longitude: `0.0`

You should get:

- effective system: `B`
- fallback: `False`

Expected houses:

| House | Expected cusp |
| --- | --- |
| H01 | `180.043331186262` |
| H02 | `215.651340496334` |
| H03 | `248.400203284023` |
| H04 | `279.159938738206` |
| H05 | `304.326984335703` |
| H06 | `331.321088710194` |
| H07 | `0.043331186262` |
| H08 | `35.651340496334` |
| H09 | `68.400203284023` |
| H10 | `99.159938738206` |
| H11 | `124.326984335703` |
| H12 | `151.321088710194` |

What this page proves
---------------------

It proves that:

- there are real experimental Placidus charts a user can run and reproduce
- there are real experimental Koch charts a user can run and reproduce
- there are real experimental Regiomontanus charts a user can run and reproduce
- there are real experimental Topocentric charts a user can run and reproduce
- there are real experimental Campanus charts a user can run and reproduce
- there are real experimental Alcabitius charts a user can run and reproduce
- experimental Regiomontanus has successful charts across the full sampled polar latitude band at Greenwich in the year 2000
- experimental Topocentric has successful charts across the full sampled polar latitude band at Greenwich in the year 2000
- experimental Campanus has successful charts across the full sampled polar latitude band at Greenwich in the year 2000
- experimental Alcabitius has successful charts across the full sampled polar latitude band at Greenwich in the year 2000
- the expected house cusps for those experiments are now recorded plainly

Proof surfaces
--------------

- [test_experimental_placidus.py](../../tests/unit/test_experimental_placidus.py)
- [experimental_placidus_greenwich_2000_2h_by_latitude.csv](/C:/Users/nilad/OneDrive/Desktop/Moira%20C++/reports/validation/experimental_placidus_greenwich_2000_2h_by_latitude.csv)
- [experimental_placidus_greenwich_2000_2h_summary.json](/C:/Users/nilad/OneDrive/Desktop/Moira%20C++/reports/validation/experimental_placidus_greenwich_2000_2h_summary.json)
- [experimental_placidus_greenwich_2000_2h_daily_calendar.csv](/C:/Users/nilad/OneDrive/Desktop/Moira%20C++/reports/validation/experimental_placidus_greenwich_2000_2h_daily_calendar.csv)
- [experimental_placidus_greenwich_2000_2h_daily_calendar_summary.json](/C:/Users/nilad/OneDrive/Desktop/Moira%20C++/reports/validation/experimental_placidus_greenwich_2000_2h_daily_calendar_summary.json)
- [test_experimental_koch.py](../../tests/unit/test_experimental_koch.py)
- [experimental_koch_greenwich_2000_2h_by_latitude.csv](/C:/Users/nilad/OneDrive/Desktop/Moira%20C++/reports/validation/experimental_koch_greenwich_2000_2h_by_latitude.csv)
- [experimental_koch_greenwich_2000_2h_summary.json](/C:/Users/nilad/OneDrive/Desktop/Moira%20C++/reports/validation/experimental_koch_greenwich_2000_2h_summary.json)
- [experimental_koch_greenwich_2000_2h_daily_calendar.csv](/C:/Users/nilad/OneDrive/Desktop/Moira%20C++/reports/validation/experimental_koch_greenwich_2000_2h_daily_calendar.csv)
- [experimental_koch_greenwich_2000_2h_daily_calendar_summary.json](/C:/Users/nilad/OneDrive/Desktop/Moira%20C++/reports/validation/experimental_koch_greenwich_2000_2h_daily_calendar_summary.json)
- [test_experimental_regiomontanus.py](../../tests/unit/test_experimental_regiomontanus.py)
- [experimental_regiomontanus_greenwich_2000_2h_by_latitude.csv](/C:/Users/nilad/OneDrive/Desktop/Moira%20C++/reports/validation/experimental_regiomontanus_greenwich_2000_2h_by_latitude.csv)
- [experimental_regiomontanus_greenwich_2000_2h_summary.json](/C:/Users/nilad/OneDrive/Desktop/Moira%20C++/reports/validation/experimental_regiomontanus_greenwich_2000_2h_summary.json)
- [experimental_regiomontanus_greenwich_2000_2h_daily_calendar.csv](/C:/Users/nilad/OneDrive/Desktop/Moira%20C++/reports/validation/experimental_regiomontanus_greenwich_2000_2h_daily_calendar.csv)
- [experimental_regiomontanus_greenwich_2000_2h_daily_calendar_summary.json](/C:/Users/nilad/OneDrive/Desktop/Moira%20C++/reports/validation/experimental_regiomontanus_greenwich_2000_2h_daily_calendar_summary.json)
- [test_experimental_topocentric.py](../../tests/unit/test_experimental_topocentric.py)
- [experimental_topocentric_greenwich_2000_2h_by_latitude.csv](/C:/Users/nilad/OneDrive/Desktop/Moira%20C++/reports/validation/experimental_topocentric_greenwich_2000_2h_by_latitude.csv)
- [experimental_topocentric_greenwich_2000_2h_summary.json](/C:/Users/nilad/OneDrive/Desktop/Moira%20C++/reports/validation/experimental_topocentric_greenwich_2000_2h_summary.json)
- [experimental_topocentric_greenwich_2000_2h_daily_calendar.csv](/C:/Users/nilad/OneDrive/Desktop/Moira%20C++/reports/validation/experimental_topocentric_greenwich_2000_2h_daily_calendar.csv)
- [experimental_topocentric_greenwich_2000_2h_daily_calendar_summary.json](/C:/Users/nilad/OneDrive/Desktop/Moira%20C++/reports/validation/experimental_topocentric_greenwich_2000_2h_daily_calendar_summary.json)
- [test_experimental_campanus.py](../../tests/unit/test_experimental_campanus.py)
- [experimental_campanus_greenwich_2000_2h_by_latitude.csv](/C:/Users/nilad/OneDrive/Desktop/Moira%20C++/reports/validation/experimental_campanus_greenwich_2000_2h_by_latitude.csv)
- [experimental_campanus_greenwich_2000_2h_summary.json](/C:/Users/nilad/OneDrive/Desktop/Moira%20C++/reports/validation/experimental_campanus_greenwich_2000_2h_summary.json)
- [experimental_campanus_greenwich_2000_2h_daily_calendar.csv](/C:/Users/nilad/OneDrive/Desktop/Moira%20C++/reports/validation/experimental_campanus_greenwich_2000_2h_daily_calendar.csv)
- [experimental_campanus_greenwich_2000_2h_daily_calendar_summary.json](/C:/Users/nilad/OneDrive/Desktop/Moira%20C++/reports/validation/experimental_campanus_greenwich_2000_2h_daily_calendar_summary.json)
- [test_experimental_alcabitius.py](../../tests/unit/test_experimental_alcabitius.py)
- [experimental_alcabitius_greenwich_2000_2h_by_latitude.csv](/C:/Users/nilad/OneDrive/Desktop/Moira%20C++/reports/validation/experimental_alcabitius_greenwich_2000_2h_by_latitude.csv)
- [experimental_alcabitius_greenwich_2000_2h_summary.json](/C:/Users/nilad/OneDrive/Desktop/Moira%20C++/reports/validation/experimental_alcabitius_greenwich_2000_2h_summary.json)
- [experimental_alcabitius_greenwich_2000_2h_daily_calendar.csv](/C:/Users/nilad/OneDrive/Desktop/Moira%20C++/reports/validation/experimental_alcabitius_greenwich_2000_2h_daily_calendar.csv)
- [experimental_alcabitius_greenwich_2000_2h_daily_calendar_summary.json](/C:/Users/nilad/OneDrive/Desktop/Moira%20C++/reports/validation/experimental_alcabitius_greenwich_2000_2h_daily_calendar_summary.json)

Verification receipt
--------------------

Checked in `.venv` with:

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_experimental_placidus.py tests/unit/test_experimental_koch.py tests/unit/test_experimental_regiomontanus.py tests/unit/test_experimental_topocentric.py tests/unit/test_experimental_campanus.py tests/unit/test_experimental_alcabitius.py -q
```

Result at time of writing:

- `58 passed`
