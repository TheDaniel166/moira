# Natal Twelfth-Parts Admission

**Verdict: admit.**
**6.3.0 placement:** new atom + REST; optional profile overlay later.

## Object

The Hellenistic dodekatemorion of an ecliptic longitude. Each 30° sign is
cut into twelve equal 2°30′ slices. The ordinary natal projection is:

    projected = (sign_start + 12 × degree_in_sign) mod 360

Seams are left-closed, right-open: `[0, 2.5)`, `[2.5, 5)`, …, `[27.5, 30)`.

## Sources

- Manilius, *Astronomica* II.693ff (the 12× rule)
- al-Biruni, *Book of Instruction* (Wright 1934) §456 (the 12× rule)
- Ptolemy, *Tetrabiblos* I.22 reports twelfth-parts and rejects them as
  unfounded; it is not an endorsing source
- Vettius Valens, *Anthologies* (Riley), multiple uses of twelfth-parts
- Dorotheus, *Carmen* I.8
- Firmicus Maternus, *Mathesis* II.17
- Skyscript / Wikipedia statement of the 12× formula (Capricorn 17° → Cancer 24°)

## Not this object

- Vedic Dwadashamsa / D12 starting-sign variants
- Abu Ma'shar Nine Parts
- Sahl/Dorotheus electional “malefic in the Moon’s twelfth-part sign”
- Chaldean faces (10°) and triplicity decans

## Fail-closed

Non-finite longitude raises. Degree 30.0 of a sign does not occur after
normalization (`longitude % 360`, then `// 30`).
