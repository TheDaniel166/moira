# Lots — Source Verification and Correction Log

Primary engine: `moira/lots.py` · `PARTS_DEFINITIONS` catalogue  
Verification method: Direct PDF extraction via PyMuPDF (fitz), `.venv` Python  
Governing formula convention: Lot = Asc + Add − Subtract (mod 360°), unless projector is otherwise stated

---

## Source Hierarchy

Verification follows the Moira authority hierarchy:

1. **Valens** — Vettius Valens, *Anthologies* (Riley translation, annotated PDF, 708 pp.)  
   Used throughout: formula pages extracted directly; planet symbols decoded from Book I.1 (pp. 25–31).
2. **Paulus** — Paulus Alexandrinus, *Introductory Matters* (PAG, Greenbaum trans.)  
   Cited in Riley footnotes; formulas cross-checked against those footnotes.
3. **Firmicus** — Firmicus Maternus, *Matheseos* (AATPB, Bram trans., Noyes Press 1975)  
   PDF acquired 2026-04-19. Full formula survey complete; 16 entries verified, 2 corrections applied (Session 2).
4. **Dorotheus** — *Carmen Astrologicum* (Pingree trans., 1976; Skyscript/Houlding OCR reproductions)  
   PDFs acquired 2026-04-21. Three volumes: Book I (dorotheus1.pdf, 21 pp.), Book II (dorotheus2.pdf, 22 pp.), Book III (dorotheus3.pdf, 7 pp.). Books IV–V (electional, interrogations) not yet acquired. Full lot survey of available text complete; 7 formulas confirmed correct, 0 corrections to lots.py this session, 2 new deferred issues (D9–D10).

---

## Planet Symbol Key (Valens / Riley translation)

Established from Book I.1 ("Nature of the Stars"), pp. 25–31:

| Symbol | Planet |
|--------|--------|
| `s` | ☉ Sun |
| `d` | ☽ Moon |
| `S` | ♄ Saturn |
| `j` | ♃ Jupiter |
| `h` | ♂ Mars |
| `g` | ♀ Venus |
| `f` | ☿ Mercury |

---

## Session 1 — Valens Full Survey (2026-04-19)

### Lots Verified Correct

All formulas confirmed against direct PDF extraction of the Riley/Valens primary text.

| Lot (lots.py name) | lots.py formula | Valens source | Page |
|--------------------|-----------------|---------------|------|
| Fortune (inline) | Asc + Moon − Sun (day) | Book II.3: "distance from s to d, from Ascendant" | 119 |
| Spirit/Daimon (inline) | Asc + Sun − Moon (day) | Book II.22: "distance from d to s (day), from Ascendant" | 170 |
| Basis (Valens) | Asc + Spirit − Fortune (day), reversed | Book II.22: "distance from Fortune to Daimon (day), from Ascendant" | 171 |
| Deceit | Asc + Mars − Sun (day), reversed | Book II.25: "distance from s to h, from Ascendant; night: opposite" | 177 |
| Debt | Asc + Saturn − Mercury | Book II.23: "distance from f to S, from Ascendant" | 175 |
| Siblings | Asc + Jupiter − Saturn (day), reversed | Book II.40: "distance from S to j (day), from Ascendant" | 240 |
| Being in a Foreign Land | Asc + Mars − Saturn | Book II.29: "distance from S to h, from Ascendant" | 187 |
| Father | Asc + Saturn − Sun (day) | Book II.30: "distance from s to S, from Ascendant" | 197 |
| Father (Alt 2) | Asc + Jupiter − Sun (day) | Book II.30: "Some determine the s to j and count from Ascendant" | 197 |
| Marriage (Valens) | Asc + Venus − Jupiter (day), reversed | Book II.37: "distance from j to g (day), from Ascendant" | 231 |
| Marriage (Men, Valens) | Asc + Venus − Sun, no reversal | Book II.38: "distance from s to g (for men), from Ascendant" | 233 |
| Marriage (Women, Valens) | Asc + Mars − Moon, no reversal | Book II.38: "distance from d to h (for women), from Ascendant" | 233 |
| Male Children (Valens) | Asc + Mercury − Jupiter, no reversal | Book II.39: "distance from j to f (male nativity), from Ascendant" | 238 |
| Female Children (Valens) | Asc + Venus − Jupiter, no reversal | Book II.39: "distance from j to g (female nativity), from Ascendant" | 238 |
| Eros (Valens) | Asc + Spirit − Fortune (day), reversed | Book IV.25 marginal note: "distance from Fortune to Daimon; night: reverse" | 396 |
| Necessity (Valens) | Asc + Fortune − Spirit (day), reversed | Book IV.25 marginal note: "distance from Daimon to Fortune; night: reverse" | 396–397 |
| Accusation / Crisis-Producing Place — *see correction* | | Book V.1 | 409 |

---

### Corrections Made

#### 1. Debt — operand swap (FIXED 2026-04-19)

**Valens II.23 (p. 175):** "The Lot of Debt is calculated by determining the distance from f [Mercury] to S [Saturn] then counting that same distance from the Ascendant."

"From Mercury to Saturn, projected from Ascendant" = Asc + Saturn − Mercury.

| | day_add | day_sub | reverse_at_night |
|--|---------|---------|-----------------|
| **Before** | Mercury | Saturn | False |
| **After** | Saturn | Mercury | False |

**Valens delineation:** Badly situated or ruler in opposition/square with malefics = native becomes a debtor. If related to Fortune, Accomplishment, or Daimon = livelihood from crime, deceit, force, or theft.

**Debtor (line 280)** carries the same operand pair (`Mercury`, `Saturn`) with `reverse_at_night=True`. Its source has not yet been verified against primary text; it was left untouched pending a dedicated check.

---

### New Entries Added

#### 2. Accusation (Valens) — new entry (ADDED 2026-04-19)

**Valens V.1 (p. 409):** "Consequently this place is strong; for day births it is found by determining the distance from S [Saturn] to h [Mars], then measuring the same distance from the Ascendant."

Night births: "from h to S" = Asc + Saturn − Mars.

Formula: day = Asc + Mars − Saturn; night = Asc + Saturn − Mars → `reverse_at_night=True`.

```python
PartDefinition("Accusation (Valens)", "Mars", "Saturn", True, "hellenistic")
```

**Placement:** After `Accusation (Firmicus)` in the catalogue.

**Valens delineation:** Malefics in aspect = precarious, endangered nativities; the sign defines the type of crisis. Benefics = lessening of evil or escape from crisis. Riley footnote also records an alternate tradition: "others measure the distance from Mercury" — a variant projector not yet in the catalogue.

**Note:** `Accusation (Firmicus)` = `("Saturn", "Mars", False)` = day: Asc + Mars − Saturn — the same day formula but without night reversal. The day formulas are identical; Valens adds the night reversal.

---

#### 3. Eros (Paulus) — new entry (ADDED 2026-04-19)

**Paulus Alexandrinus, PAG ch. 23**, cited in Riley footnote (Valens p. 354):  
"The Lot of Love/Eros is from Daimon to g [Venus]."

= Asc + Venus − Daimon = Asc + Venus − Spirit

No night reversal stated in the cited source.

```python
PartDefinition("Eros (Paulus)", "Venus", "Spirit", False, "hellenistic")
```

**Placement:** After `Eros (Olympiodorus) B`, before `Eros (Valens)`.

**Relationship to other Eros entries:**  
- `Eros (Valens)` = Asc + Spirit − Fortune (day). Operationally different — uses Fortune as subtractive, Daimon (Spirit) as additive.  
- `Eros (Paulus)` = Asc + Venus − Spirit. Uses Venus directly rather than deriving from the lot pair.

---

#### 4. Necessity (Paulus) — new entry (ADDED 2026-04-19)

**Paulus Alexandrinus, PAG ch. 23**, cited in Riley footnote (Valens p. 354):  
"The Lot of Necessity is taken from Fortune to f [Mercury]."

= Asc + Mercury − Fortune

No night reversal stated in the cited source.

```python
PartDefinition("Necessity (Paulus)", "Mercury", "Fortune", False, "hellenistic")
```

**Placement:** After `Necessity (Hermetic)`, before `Necessity (Persian)`.

**Relationship to other Necessity entries:**  
- `Necessity (Valens)` = Asc + Fortune − Spirit (day). Operationally the inverse in structure.  
- `Necessity (Hermetic)` = Asc + Fortune − Mercury (day). This is the reverse operand order from the Paulus formula; source text not yet verified.

---

### Deferred Issues (not corrected — structural or unresolved)

#### D1. Theft (Valens) — wrong projector (DEFERRED)

**Valens II.24 (p. 176):** "For day births, the position of the Lot is calculated by determining the distance from f [Mercury] to h [Mars], then counting the same distance from **S [Saturn]**; for night births, measure from h to f, then from S."

The projector is **Saturn**, not the Ascendant. The current `PartDefinition` engine expresses all lots as `Asc + Add − Sub`. There is no field for an alternate projector. The formula as Valens gives it cannot be correctly implemented without an engine extension.

**Current lots.py entry:**  
```python
PartDefinition("Theft (Valens)", "Mars", "Mercury", True, "hellenistic")
# Computes: Asc + Mars - Mercury (day)
# Should be: Saturn + Mercury - Mars (day), Saturn + Mars - Mercury (night)
```

**What is wrong:** Both the projector (Asc vs. Saturn) and the operand direction are incorrect for the day formula.

**Theft (Olympiodorus)** (line 669) holds an identical formula `("Mars", "Mercury", True)`. If Olympiodorus uses Ascendant as projector and Valens uses Saturn, these are genuinely distinct lots sharing a formula incorrectly. Source for Olympiodorus not yet verified.

**Resolution path:**  
1. Verify Olympiodorus formula in PAG.  
2. Decide whether to add a `projector` field to `PartDefinition` or handle Theft (Valens) as a special-cased lot in the computation engine.  
3. Until resolved, both entries are flagged as formula-incorrect for the Valens variant.

---

#### D2. Basis (Valens) — shortest-arc rule not implemented (DEFERRED)

**Valens II.22 (p. 171):** "The distance will not exceed the number 7 [≤7 signs] for night or day births but it is necessary to take the distance from the nearest Lot to the other Lot."

Riley footnote: "Take the shortest distance between the two lots. This results in the Lot of Basis always falling below the horizon."

lots.py computes `Asc + Spirit − Fortune` using standard directional arc arithmetic. The shortest-arc constraint is not implemented. The formula is correct; the distance modulation is not captured.

**Resolution path:** Requires either a per-lot post-computation clamp, or a new flag on `PartDefinition` for shortest-arc semantics.

---

#### D3. Mother — day/night assignment (DOCTRINAL NUANCE)

**Valens II.30 (p. 197):** "For night births, determine the distance from g [Venus] to the d [Moon] and count this distance from the Ascendant." 

Valens gives **only a night formula**. No day formula is stated. lots.py `Mother = ("Moon", "Venus", True)` uses the Valens night formula as the day formula and inverts it for night. Source for the day assignment is unverified.

---

---

## Session 2 — Firmicus Maternus Survey (2026-04-19)

**Source:** Firmicus Maternus, *Ancient Astrology: Theory and Practice* (*Mathesis*), trans. Jean Rhys Bram (Noyes Press, 1975). PDF `firmicusmaternustheoryandpractice.pdf`, 340 pages.

**Survey method:** Full-document keyword scan for formula language ("count from," "part of," "lot of," "from the degree of"), followed by targeted extraction of all formula-bearing sections:
- Book III.14 (p. 119): Moon in the Part of Fortune
- Book IV.17–18 (pp. 139–141): Part of Fortune; Part of the Daemon
- Book VI.32 §§19–57 (pp. 226–229): Meanings of Houses — dedicated lot formula catalogue
- Book VII.9–12, 25 (pp. 249–252, 266–269): Parents, Siblings, Marriage, Sexual Desire
- Book VII.11 §6 (p. 250): Alternate Brothers formula

**Formula convention in Firmicus:** Most lots stated as "count from X to Y and then from the Ascendant." Day/night reversal is explicit when present ("by day… by night…"). Absence of qualifier + "always" = no reversal.

---

### Lots Verified Correct (Firmicus)

All formula references are to Bram's translation sections; PDF page numbers in parentheses.

| Lot (lots.py name) | lots.py formula | Firmicus source | Section |
|--------------------|-----------------|-----------------|---------|
| Fortune (inline) | Asc + Moon − Sun (day), reversed | IV.17 §3–4: "count from Sun to Moon (day)" | (p. 139) |
| Mother | Asc + Moon − Venus (day), reversed | VI.32 §21–22: "from Venus to Moon (day); from Moon to Venus (night)" | (p. 226) |
| Siblings | Asc + Jupiter − Saturn (day), reversed | VI.32 §23: "from Saturn to Jupiter (day); from Jupiter to Saturn (night)" | (p. 226) |
| Siblings (Firmicus) | Asc + Sun − Mercury, no reversal | VII.11 §6: "count from Mercury to the Sun" | (p. 250) |
| Marriage (Firmicus) | Asc + Moon − Sun, no reversal | VI.32 §28: "some count from Sun to Moon both diurnal and nocturnal" | (p. 227) |
| Marriage (Men, Dorotheus) | Asc + Venus − Saturn (day), reversed | VI.32 §27: "from Saturn to Venus (day)" | (p. 226–227) |
| The Husband | Asc + Venus − Mars (day), reversed | VI.32 §32: "from Mars to Venus (day); from Venus to Mars (night)" | (p. 227) |
| Children (Firmicus)(Alt) | Asc + Mercury − Jupiter (day), reversed | VI.32 §35: alt "from Jupiter to Mercury (day); Mercury to Jupiter (night)" | (p. 227) |
| Illness (Dorotheus) | Asc + Mars − Saturn (day), reversed | VI.32 §40: "from Saturn to Mars (day); from Mars to Saturn (night)" | (p. 228) |
| Eros (Firmicus) | Asc + Fortune − Spirit (day), reversed | VI.32 §45: "from Daemon to Fortune (day)" (= house of sexual desire) | (p. 229) |
| Necessity (Firmicus) | Asc + Spirit − Fortune (day), reversed | VI.32 §46: "from Fortune to Daemon (day)" | (p. 229) |
| Substance and Possessions | Asc + Jupiter − Mercury, no reversal | VI.32 §52: "from Mercury to Jupiter" | (p. 229) |
| Accusation (Firmicus) | Asc + Saturn − Mars, no reversal | VI.32 §53: "from Mars to Saturn" | (p. 229) |
| Enemies (Firmicus) | Asc + Mercury − Mars (day), reversed | VI.32 §54: "from Mars to Mercury (day); Mercury to Mars (night)" | (p. 229) |
| Nemesis (Firmicus) | Asc + Fortune − Moon (day), reversed | VI.32 §56: "by night from Fortune to Moon" → night formula = Asc + Moon − Fortune | (p. 229) |
| Power | Asc + Saturn − Sun (day), reversed | VI.32 §56: "by night from Saturn to Sun" | (p. 229) |

---

### Corrections Made (Firmicus Session)

#### 5. Friends (Firmicus) — `reverse_at_night` False → True (FIXED 2026-04-19)

**Firmicus VI.32 §55 (p. 229):** "If you wish to locate exactly the house of friends, by day count from Jupiter to Mercury, by night from Mercury to Jupiter."

This is an explicit day/night reversal instruction. The existing entry had `reverse_at_night=False`, meaning the night formula was identical to the day formula.

| | day_add | day_sub | reverse_at_night |
|--|---------|---------|-----------------|
| **Before** | Mercury | Jupiter | **False** |
| **After** | Mercury | Jupiter | **True** |

Day: Asc + Mercury − Jupiter (Jupiter→Mercury) ✓  
Night (reversed): Asc + Jupiter − Mercury (Mercury→Jupiter) ✓

---

#### 6. Travel (Firmicus) — `reverse_at_night` True → False (FIXED 2026-04-19)

**Firmicus VI.32 §49 (p. 229):** "If you wish to locate the house of travel, **always** count from the Sun to Mars and again from the ascendant."

The word "always" (contrasting with §54's "by day… by night…" for Enemies) signifies a single formula with no day/night inversion. The existing entry had `reverse_at_night=True`.

| | day_add | day_sub | reverse_at_night |
|--|---------|---------|-----------------|
| **Before** | Mars | Sun | **True** |
| **After** | Mars | Sun | **False** |

Formula (always): Asc + Mars − Sun ✓

---

### Deferred / Uncertain (Firmicus Session)

#### D4. Firmicus IV.18 — Daemon formula appears to duplicate Fortune (DOCTRINAL NOTE)

**Firmicus IV.18 §1 (p. 141) in Bram:** "in a diurnal chart count the degrees of every sign from the Sun to the Moon… that is the Part of the Daemon."

This is identical to the Fortune formula (IV.17 §3). The standard Hellenistic formula for Daemon is Asc + Sun − Moon (day), the reverse of Fortune. This is almost certainly a translation error or manuscript variant in Bram. The correct Daemon formula (Asc + Sun − Moon, day; reversed night) is already correctly implemented in lots.py inline computation. No change required; note recorded for bibliographic honesty.

#### D5. Military Service (Firmicus) — reversal source uncertain (NOTED)

**Firmicus VI.32 §48 (p. 229):** "count from Mars to the Sun" — no day/night qualifier, no "always." Formula: Asc + Sun − Mars.

lots.py entry has `reverse_at_night=True`. This may reflect a general convention (lots without explicit qualifier follow day/night reversal) rather than a Firmicus-specific instruction. The night formula (Asc + Mars − Sun) is not attested in Firmicus. Status: **uncertain, not changed pending cross-reference with Dorotheus/Paulus.**

#### D6. Slaves — "always" formula vs. rev=True on existing entry (NOTED)

**Firmicus VI.32 §57 (p. 229):** "count **always** from Mercury to the Moon" = Asc + Moon − Mercury, no reversal.

`Slaves (Dorotheus)` in lots.py: `add=Moon, sub=Mercury, rev=True`. The day formula matches Firmicus but the night reversal does not. No `Slaves (Firmicus)` entry exists. Since the entry is attributed to Dorotheus (not Firmicus), this may be intentional. To be verified against Dorotheus primary text.

#### D7. Physical Courage — Firmicus formula missing (NOTED)

**Firmicus VI.32 §51 (p. 229):** "count from the Moon to Jupiter" = Asc + Jupiter − Moon, no reversal stated.

No entry matching this formula with this attribution exists in lots.py. `Courage` = `(Fortune, Mars, True)` is a different formula. `Courage, Violence & Combat` = `(Moon, Ruler Asc, True)` is also different. A `Courage (Firmicus)` entry with `("Jupiter", "Moon", False)` is absent. **Not added in this session** — the lot is unnamed in the text ("house of physical courage" is the translator's label) and the lot name/attribution requires cross-reference before adding.

#### D8. Glory — Firmicus formula missing (NOTED)

**Firmicus VI.32 §56 (p. 229):** "for the house of glory, count by night from Venus to Jupiter, by day the opposite."  
Night: Venus→Jupiter = Asc + Jupiter − Venus.  
Day: Jupiter→Venus = Asc + Venus − Jupiter.

No `Glory (Firmicus)` entry in lots.py. Not added in this session — the lot name requires cross-reference to confirm this is the same concept as other "glory/fame" entries in the catalogue.

---

## Session 3 — Dorotheus Survey (2026-04-21)

**Source:** Dorotheus of Sidon, *Carmen Astrologicum*, Book I–III. Trans. David Pingree, 1976 (BSB B.G. Teubner Verlagsgesellschaft). OCR reproductions compiled by Deborah Houlding, Skyscript.co.uk (personal study use only).

**Volume contents:**
- `dorotheus1.pdf` (21 pp.) = Skyscript `dorotheus1.pdf` = **Book I** (Carmen chapters I.1–I.28: natal judgments, lots of father/mother/siblings/fortune/property). Pingree pages ~p.161–p.195.
- `dorotheus2.pdf` (22 pp.) = Skyscript `dorotheus2.pdf` = **Book II** (II.1–II.33: marriage, children, placement of planets). Pingree pages ~p.197–p.224.
- `dorotheus3.pdf` (7 pp.) = Skyscript `dorotheus3.pdf` = **Book III** (III.1–III.2: haylāj/hyleg and length of life). Pingree pages p.235–p.245.
- **Books IV–V not acquired** (electional astrology, interrogations). Lot formulas in those books are not surveyed.

**Survey method:** Full text extracted via PyMuPDF for all three PDFs. All pages scanned for formula language patterns: "count from," "lot of," explicit planet-name operand pairs, "add to it the degrees of the ascendent," "subtract from the ascendent." All formula-bearing pages read in full. Results compared against lots.py `PARTS_DEFINITIONS`.

**Formula convention in Dorotheus/Pingree:**
- "count from X to Y and add to it the degrees of the ascendent [by day]" = Asc + Y − X  
- "and subtract it from the ascendent [by night]" = Asc − (Y − X) = Asc + X − Y → **reversal confirmed**  
- Night formula with *reversed arc direction* + "subtract from ascendent" = two inversions cancel → **no net reversal**  
- Absence of day/night qualifier = no reversal

---

### Lot of Fortune — Dorotheus I.26 (verified)

**Dorotheus I.26 (Pingree p.191):** "For him whose birth is in the day count from the Sun to the Moon and add to it the degrees of the ascendent, and in a nocturnal nativity the opposite of this."

Day: Asc + Moon − Sun. Night ("the opposite"): Asc + Sun − Moon.

**Matches** lots.py inline computation (`_build_refs`). ✓

---

### Lots Verified Correct (Dorotheus)

| Lot (lots.py name) | lots.py formula | Dorotheus source | Location |
|--------------------|-----------------|-----------------|----------|
| Siblings | Asc + Jupiter − Saturn (day), reversed | I.19: "from Saturn to Jupiter [day]; subtract [night]" | Pingree p.178 |
| Father | Asc + Saturn − Sun (day) | I.13: "from Sun to Saturn + Asc [day]; from Saturn to Sun, subtract [night]" | Pingree p.174 |
| Children | Asc + Saturn − Jupiter (day), reversed | II.10: "from Jupiter to Saturn + Asc [day]; subtract [night]" | Pingree p.209 |
| Male Children (Dorotheus) | Asc + Sun − Jupiter, no reversal | II.12: "degrees between Jupiter and Sun + Asc" (no day/night qualifier) | Pingree p.210 |
| Female Children (Dorotheus) | Asc + Venus − Moon (day), reversed | II.12: "from Moon to Venus + Asc [day]; subtract [night]" | Pingree p.210 |
| Marriage (Men, Dorotheus) | Asc + Venus − Saturn (day), reversed | II.2: "from Saturn to Venus + Asc [day]; subtract [night]" | Pingree p.199 |
| Illness (Dorotheus) | Asc + Mars − Saturn (day), reversed | Not found in Dorotheus text; formula confirmed via Firmicus cross-reference (§40) ← prior session | — |

**Note on Father (I.13):** Dorotheus gives "from Sun to Saturn + Asc [by day]" = Asc + Saturn − Sun; then for night: "from Saturn to Sun, subtract from Asc" = Asc − (Sun − Saturn) = Asc + Saturn − Sun. Both resolve to **the same formula**; there is **no day/night reversal** in Dorotheus. lots.py `Father = ("Saturn", "Sun", True)` carries `reverse_at_night=True`, meaning lots.py follows a different tradition (Valens Book II.30 gives the same day formula; reversal may originate there). The lots.py entry is attributed broadly ("hellenistic,medieval"), not specifically to Dorotheus, so no correction is required; the discrepancy is doctrinal.

**Note on Illness (Dorotheus):** The formula is referenced in Dorotheus II.7 as a pre-existing lot ("the lot of illness") but not defined there. No explicit definition was found in Books I, II, or III. The Firmicus cross-reference (Session 2, §40) confirms Saturn→Mars day / Mars→Saturn night, which matches the current lots.py entry. The Dorotheus attribution in the lot name remains unverified from Dorotheus primary text.

**Note on Male Children operand direction (II.12):** "Count what of degrees is between Jupiter and the Sun" — in Arabic astrological convention, "between A and B" = arc from A to B going direct. Arc from Jupiter to Sun = Sun − Jupiter → Asc + Sun − Jupiter. This matches lots.py `("Sun", "Jupiter", False)`. The companion entry `Male Children (Dorotheus - Chinese) = ("Jupiter", "Sun", False)` represents the reversed-operand reading and does not match Dorotheus II.12.

---

### Observations Without Correction

#### Mother lot vs. Dorotheus I.14

**Dorotheus I.14 (Pingree p.174–175):**  
"Calculate the lot of the mother in a nocturnal birth from the Moon to Venus and in the daytime from Venus to the Moon, and **add to it the degrees of the ascendent [by night]** or **subtract [it] from the ascendent [by day]**."

Computation:  
- Night: from Moon to Venus + Asc = Asc + Venus − Moon  
- Day: from Venus to Moon, subtract from Asc = Asc − (Moon − Venus) = Asc + Venus − Moon  

Both resolve to **Asc + Venus − Moon with no day/night reversal**.

**lots.py `Mother = ("Moon", "Venus", True)`:**  
- Day: Asc + Moon − Venus  
- Night: Asc + Venus − Moon  

The night formula matches Dorotheus. The day formula **disagrees** — Dorotheus says Asc + Venus − Moon both by day and by night; lots.py gives Asc + Moon − Venus by day.

**Prior session cross-reference:** Firmicus VI.32 §21–22 (Session 2) says "from Venus to Moon (day)" = Asc + Moon − Venus. lots.py follows Firmicus for the day formula, not Dorotheus.

**Decision:** No correction. The `Mother` entry is attributed broadly ("hellenistic,medieval") and correctly reflects the Firmicus tradition. A `Mother (Dorotheus)` entry with `("Venus", "Moon", False)` could be considered if doctrinal completeness requires it. Deferred — not added in this session.

#### Marriage (Women, Dorotheus) — reversal unconfirmed from Dorotheus II.3

**Dorotheus II.3 (Pingree p.199):** "If you want to see in the nativity of a woman the lot of marriage, then count from the degrees of Venus to Saturn and **add to it the degrees of the ascendent**." No day/night qualifier.

Formula as stated: Asc + Saturn − Venus (always). Day formula matches lots.py `("Saturn", "Venus", True)` day formula ✓. The `reverse_at_night=True` in the lots.py entry is **not supported** by Dorotheus II.3 alone — no night reversal instruction appears in this chapter. The reversal may come from another tradition (the men's formula in II.2 has explicit reversal; women's may be assumed symmetric). Document as observation. No correction in this session.

---

### New Deferred Issues

#### D9. Siblings (Number) — reversal missing in lots.py (DEFERRED)

**Dorotheus I.21 (Pingree p.180):** "Count from the degree in which Mercury is to Jupiter, and add to it the degrees of the ascendent **[by day]** or **subtract it from the ascendent thirty [degrees at a time] [by night]**."

Day: Asc + Jupiter − Mercury. Night: Asc − (Jupiter − Mercury) = Asc + Mercury − Jupiter. This is a **confirmed reversal**.

**lots.py entry (line 632):**  
```python
PartDefinition("Siblings (Number)", "Jupiter", "Mercury", False, "hellenistic,medieval")
```
Day formula matches Dorotheus. The `False` value omits the night reversal.

**Resolution path:** Confirm against Paulus/Valens before changing. If other Hellenistic sources agree with Dorotheus, change `False` → `True`.

---

#### D10. Time of Children — reversal missing in lots.py (DEFERRED)

**Dorotheus II.11 (Pingree p.209–210):** "Count from Mars to Jupiter and add to it the degrees of the ascendent **[by day]** or **subtract it from the ascendent [by night]**, thirty at a time."

Day: Asc + Jupiter − Mars. Night: Asc − (Jupiter − Mars) = Asc + Mars − Jupiter. This is a **confirmed reversal**.

**lots.py entry (line 679):**  
```python
PartDefinition("Time of Children", "Jupiter", "Mars", False, "hellenistic,medieval")
```
Day formula matches Dorotheus. The `False` value omits the night reversal.

**Resolution path:** Confirm against Paulus/Valens before changing. If other Hellenistic sources agree with Dorotheus, change `False` → `True`.

---

---

## Session 4 — Bonatti PDF Triage (2026-04-19)

**Source presented:** `bonatti146.pdf` — *Anima Astrologiae, or A Guide for Astrologers: Being the One Hundred and Forty-Six Considerations of the Famous Astrologer Guido Bonatus*. Translated from Latin by Henry Coley, 1675. William Lilly prefatory address dated 2 August 1675. Skyscript/STA scan.

**Finding: Wrong Bonatti work.**

This PDF contains the *146 Considerations* (*Anima Astrologiae*) — a collection of horary and natal aphorisms, not a lot formula catalogue. It makes three references to the Part of Fortune as an interpreter's significator in horary judgment (Considerations 85, 103, 122) and one generic formula for constructing an ad hoc lot from any two significators (Consideration 140: "subtract the lesser from the greater, and add to the remainder the degrees of the sign Ascending, and project what they amount unto from the Ascendant"). None of these define operand pairs for any named Arabic Part.

**The required source is *Liber Astronomiae* (*The Book of Astronomy*), Bonatti's full treatise.** The Arabic Part formula catalogue is in the *Liber Astronomiae*, Part I (Tractatus I), specifically in his discussion of the lots — typically translated by Benjamin Dykes (2010, Cazimi Press). The 146 Considerations are an appendix / distillation abstracted from the larger work; they contain no lot formula tables.

**Result: No lots.py entries verified or corrected this session. No changes to lots.py.**

---

---

## Session 5 — al-Biruni Survey (2026-04-19)

**Source:** *Kitāb al-Tafhīm li-Awāʾil Ṣināʿat al-Tanjīm* (Book of Instruction in the Elements of the Art of Astrology), Abū'l-Rayḥān Muḥammad ibn Aḥmad al-Bīrūnī. Translation: R. Ramsay Wright, Luzac & Co., London, 1934. Facsimile scan of Brit. Mus. MS. Or. 8349.

**Method:** Pages rendered as 2.5× PNG via PyMuPDF (`fitz`); lot table pages read visually. OCR extraction alone was insufficient due to garbled planet symbols in the 1934 typeset scan.

**Relevant sections:** §§475–478 (pp. 72–84 in the Wright pagination):
- §475: Part of Fortune — detailed arithmetic derivation (Ptolemaic method)
- §476: Table of 97 lots (7 universal, 80 by house, 10 "not belonging to planets or houses") — explicitly attributed to Abū Maʿshar (*Madkhal Kabīr*). **al-Bīrūnī is editing and reproducing Abū Maʿshar here, not presenting his own original lot list.**
- §477: "Differences in practice" — alternate operands (e.g. Saturn under rays → use Jupiter/Sun for Parents lot)
- §478: Additional lots cast at world-year ingress and lunar conjunctions/oppositions

**Table convention (§476 formula):**  
`Lot = Place 3 + Place 2 − Place 1`  
where Place 1 = starting point (= `day_sub`), Place 2 = ending point (= `day_add`), Place 3 = Ascendant.  
Column header "Diurnal or Nocturnal: **change**" = `reverse_at_night = True`; "**same**" = `False`.

---

### Confirmed Matches (lots.py correct per al-Bīrūnī)

All 7 Universal Lots (Greek names in footnote 1):

| # | al-Bīrūnī Name | P1 → P2 | Rev | lots.py Entry | Status |
|---|----------------|---------|-----|---------------|--------|
| 1 | Fortune (Τύχη) | ☉ → ☽ | change | inline Fortune | ✓ |
| 2 | Daemon (Δαίμων) | ☽ → ☉ | change | inline Spirit | ✓ |
| 3 | Eros (Ἔρως) | ⊕ → Ω | change | `Eros (Valens)`: Spirit-Fortune, rev=True | ✓ |
| 4 | Ananke (Ἀνάγκη) | Ω → ⊕ | change | `Necessity (Valens)`: Fortune-Spirit, rev=True | ✓ |
| 5 | Nemesis (Νέμεσις) | ♄ → ⊕ | change | `Nemesis`: Fortune-Saturn, rev=True | ✓ |
| 6 | Nike (Νίκη) | Ω → ♃ | change | `Victory`: Jupiter-Spirit, rev=True | ✓ |
| 7 | Tolma (Τόλμα) | ♂ → ⊕ | change | `Courage`: Fortune-Mars, rev=True | ✓ |

Additional house-lot matches:

| # | al-Bīrūnī Name | P1 → P2 | Rev | lots.py Entry | Status |
|---|----------------|---------|-----|---------------|--------|
| 8 | Life (1st) | ♃ → ♄ | change | `Life 1`: Saturn-Jupiter, rev=True | ✓ |
| 10 | Reasoning & eloquence (1st) | ☿ → ♂ | change | `Logic & Reason`: Mars-Mercury, rev=True | ✓ |
| 14 | Brothers (3rd) | ♄ → ♃ | change | `Siblings`: Jupiter-Saturn, rev=True | ✓ |
| 23 | Agriculture (4th) | ♀ → ♄ | same | `Agriculture`: Saturn-Venus, rev=False | ✓ |
| 30 | Disease — Hermes (6th) | ♄ → ♂ | change | `Illness (Dorotheus)`: Mars-Saturn, rev=True | ✓ |
| 34 | Marriage of men — Hermes (7th) | ♄ → ♀ | change | `Marriage (Men, Dorotheus)`: Venus-Saturn, rev=True | ✓ |
| 38 | Marriage of women — Hermes (7th) | ♀ → ♄ | change | `Marriage (Women, Dorotheus)`: Saturn-Venus, rev=True | ✓ |
| 60 | Traditions/knowledge (9th) | ☉ → ♃ | change | `Tales, Knowledge of Rumors`: Jupiter-Sun, rev=True | ✓ |
| 71 | Buying and selling (10th) | Ω → ⊕ | change | `Business, Buying & Selling`: Fortune-Spirit, rev=True | ✓ |
| 73 | Mothers (10th) | ♀ → ☽ | change | `Mother`: Moon-Venus, rev=True | ✓ |

---

### Deferred Issues Raised

**D11 — Debt naming / operand direction disagreement:**  
al-Bīrūnī #12 "Debt": ♄ → ☿ = Asc + Mercury − Saturn, change (rev=True).  
This formula matches lots.py **`Debtor`** (Mercury-Saturn, rev=True). It does **not** match lots.py **`Debt`** (Saturn-Mercury, rev=False), which Session 1 set per Valens II.23.  
Conversely, al-Bīrūnī #97 "Rectitude": ☿ → ♄ = Asc + Saturn − Mercury, change — the same operand direction as lots.py `Debt` but with change (rev=True), not rev=False.  
**Consequence:** Either (a) Valens II.23 and al-Bīrūnī agree on the formula but use different lot names, or (b) the Session 1 operand swap was an error. Cannot resolve without re-reading Valens II.23 directly. Pending Valens re-examination.

**D12 — Illness (Ancients) sub-operand:**  
al-Bīrūnī #31 "Disease a/o to some of the ancients": ♀ → ♂ = Asc + Mars − Venus, same (rev=False).  
lots.py `Illness (Ancients)`: add=Mars, sub=**Mercury** = Asc + Mars − Mercury, rev=False.  
Operands agree on direction (Mars as day_add, no reversal) but the day_sub differs: Venus (al-Bīrūnī) vs Mercury (lots.py). If al-Bīrūnī is the source for this entry, the sub should be Venus. Pending source identification for the lots.py attribution "Ancients."

**D13 — Marriage (Men, Valens) reversal:**  
al-Bīrūnī #35 "Marriage a/o Wallis [Vettius Valens]": ☉ → ♀ = Asc + Venus − Sun, **change** (rev=True).  
lots.py `Marriage (Men, Valens)`: Venus-Sun, rev=**False**. Operands match; reversal disagrees.  
Valens outranks al-Bīrūnī; pending Valens re-examination before correcting.

**D14 — Marriage (Women, Valens) reversal:**  
al-Bīrūnī #39 "Marriage of women (Valens)": ☽ → ♂ = Asc + Mars − Moon, **change** (rev=True).  
lots.py `Marriage (Women, Valens)`: Mars-Moon, rev=**False**. Operands match; reversal disagrees.  
Valens outranks al-Bīrūnī; pending Valens re-examination.

**D15 — Knowledge direction and reversal:**  
al-Bīrūnī #61 "Knowledge whether true or false": ♃ → ☽ = Asc + Moon − Jupiter, **same** (rev=False).  
lots.py `Knowledge`: add=Jupiter, sub=Moon = Asc + Jupiter − Moon, rev=**True**.  
Both operand direction and reversal flag differ. Category in lots.py is "medieval,mundane," which may indicate a different tradition (mundane astrology) rather than nativity use; the al-Bīrūnī entry is in the 9th house section (nativity context). Pending source identification.

---

### Engine Limitation Notes (not correctable without engine extension)

Several al-Bīrūnī lots use house cusps or derived points as operands — outside the current `PartDefinition` planet-only model:
- #11 Property: Lord of II, Cusp of II
- #16 Death of brothers: ☉ → 10° of III (fixed house degree)
- #32 Captivity: Lord of time + Lord of VI (compound)
- #50 Death: ☽ → Cusp VIII, cast from degree of ♄ (non-Ascendant projector)
- #55 Journeys: Lord IX → Cusp IX
- #62 Noble births: Lord of time → degree of exaltation (conditional)
- #86 Enmity (Hermes): Lord XII → Cusp XII
- #91 Boldness: Lord Asc → ☽

These are noted for future engine extension work, not this session.

---

**Result: No lots.py entries changed this session.** 14 lots confirmed correct; 5 new deferred issues raised (D11–D15).

---

---

## Open Verification Work

Sources not yet directly checked against primary text:

- [x] Firmicus entries — *Matheseos* (AATPB) — **surveyed 2026-04-19; see Session 2 above**
- [x] Dorotheus entries — *Carmen Astrologicum*, Books I–III — **surveyed 2026-04-21; see Session 3 above** (Books IV–V not yet acquired)
- [ ] Olympiodorus entries — PAG (Greenbaum)
- [ ] Bonatti entries — *Liber Astronomiae* (**wrong PDF acquired; see Session 4 note**)
- [x] al-Biruni entries — *Kitāb al-Tafhīm* (Wright 1934, §476 table) — **surveyed 2026-04-19; see Session 5 above**
- [ ] `Debtor` formula source
- [ ] `Necessity (Hermetic)` operand direction vs. Paulus
- [ ] Theft (Olympiodorus) formula per PAG
- [ ] Accusation / Crisis alternate tradition ("from Mercury") per Riley footnote, Valens p. 409
- [ ] Military Service (Firmicus) reversal — cross-check Dorotheus/Paulus (D5) — Dorotheus Books IV–V not yet available
- [ ] Slaves (Dorotheus) reversal vs. Firmicus "always" (D6) — not found in available Dorotheus text; awaiting Books IV–V
- [ ] Mother (Dorotheus) — formula Asc + Venus − Moon (no reversal) per I.14; consideration of `Mother (Dorotheus)` entry pending
- [ ] Physical Courage (Firmicus §51: Moon→Jupiter) — name/attribution before adding (D7)
- [ ] Glory (Firmicus §56: day Jupiter→Venus, night Venus→Jupiter) — name/attribution before adding (D8)
- [ ] Siblings (Number) `False` → `True`? — confirm against Paulus/Valens before changing (D9)
- [ ] Time of Children `False` → `True`? — confirm against Paulus/Valens before changing (D10)
- [ ] Marriage (Women, Dorotheus) reversal source — II.3 gives no qualifier; cross-check Paulus/Valens
- [ ] Debt naming & operand direction — Valens II.23 vs al-Bīrūnī #12; `Debtor` formula matches al-Bīrūnī Debt; `Debt` formula matches al-Bīrūnī Rectitude — needs Valens II.23 re-read (D11)
- [ ] Illness (Ancients) sub: Mercury (lots.py) vs Venus (al-Bīrūnī #31) — needs source identification for lots.py attribution (D12)
- [ ] Marriage (Men, Valens) rev=False vs al-Bīrūnī #35 change — Valens re-verification before correcting (D13)
- [ ] Marriage (Women, Valens) rev=False vs al-Bīrūnī #39 change — Valens re-verification before correcting (D14)
- [ ] Knowledge direction: lots.py Jupiter-Moon vs al-Bīrūnī #61 Moon-Jupiter; also reversal differs — source identification needed (D15)
