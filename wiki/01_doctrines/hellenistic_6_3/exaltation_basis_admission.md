# Exaltation and Basis Supporting-Lots Admission

**Verdict: admit as supporting lots.**
**6.3.0 placement:** helpers over the existing catalogue. Do **not** change
`HELLENISTIC_PROFILE_LOTS`.

## Objects

- `Exaltation (Day)`: projector 18° Aries, operand Sun, no night reverse
- `Exaltation (Night)`: projector 2° Taurus, operand Moon, no night reverse
- `Basis (Valens)`: shorter Fortune/Spirit interval from the Ascendant
  (`LotArcPolicy.SHORTEST`), Valens II.22

A day chart uses Day; a night chart uses Night. Both raw names remain in
the catalogue. Hellenistic selection must use horizon-frame sect, not
`LotsService.is_day_chart`.

## Sources

- Valens II.22 (Riley) for Basis
- Catalogue already encodes the two Exaltation formulae

## Not this object

- Adding a fifth/sixth name to the closed profile partition
- Admitting lot astrological condition (`no_admitted_lot_condition_doctrine` stays)
- Firmicus Basis as a silent alias
