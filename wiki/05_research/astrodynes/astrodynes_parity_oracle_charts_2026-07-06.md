# Astrodynes Parity-Oracle Charts (2026-07-06)

Status: executable end-to-end oracle (secondary / software source; validated
2026-07-12)

Purpose:
- capture three complete worked astrodyne charts supplied on 2026-07-06 as
  executable end-to-end validation oracles
- these close the practical need for full-chart fixtures with *captured inputs*,
  which the manual's own worked chart (Benjamine) lacked (its input positions are
  only a wheel image)

Classification and authority:
- Source: *Astrological Delineation with Astrodynes: Class 1 - The Planets*, a
  Church of Light class handout. The three chart reports are computer-generated
  Church of Light astrodyne output.
- This is a **secondary (software) oracle**. It is Church-of-Light-authoritative
  in doctrine, but it is not the manual's hand-derivation. Per the parity law,
  the manual's discrete hand-worked examples
  (`astrodynes_worked_examples_capture_2026-07-06.md`) remain the **primary**
  term-by-term validation; these three charts are corroborating end-to-end
  targets.

---

## 1. Confidence Basis (internal checksum)

The manual requires that, within rounding, the total chart power computed six
independent ways is equal: sum(sign power) = sum(house power) = sum(society
power) = sum(trinity power) = sum(element power) = sum(quality power). Every one
of the three captured charts satisfies this:

- Donald Trump: all six aggregations sum to 784.05
- Mohandas Gandhi: all six aggregations sum to 1002.47
- Barbara Walters: all six aggregations sum to 784.78

On 2026-07-12 the official PDF pages were rendered directly. The wheels and
grids were digit-verified and frozen in
`tests/fixtures/astrodynes_church_of_light.json`. The upper grid triangles
provide zodiacal relations and the lower triangles provide parallels. The
wheel cusps identify Placidus figures. The executable results and tolerances are
recorded in
`astrodynes_three_chart_parity_validation_2026-07-12.md`.

---

## 2. Chart A - Donald Trump

Birth data: 1949-06-14, 9:51 a.m., Queens, New York.

Source-defect note (2026-07-12): the page prints 1949, but all ten planetary
positions demonstrate the wheel is for 1946-06-14 9:51 a.m. EDT. The fixture
preserves the literal label and uses the wheel-demonstrated 1946 epoch only for
the otherwise unprinted declinations.

Planet positions (decoded from the wheel; verify against image):
- Sun 22 Gemini 53; Moon 20 Sagittarius 41; Mercury 8 Cancer 46;
  Venus 25 Cancer 41; Mars 26 Leo 45; Jupiter 17 Libra 27 R;
  Saturn 23 Cancer 48; Uranus 17 Gemini 53; Neptune 5 Libra 50 R;
  Pluto 10 Leo 02.
- Mercury is in Cancer, so this chart does not test the disputed Mercury
  exaltation sign.

Planets (power / % / net harmony):
Sun 82.08 / 15.3 / -4.96; Moon 80.47 / 15.0 / -5.97; Uranus 73.85 / 13.8 / 13.04;
Asc 47.10 / 8.8 / 22.19; MC 43.27 / 8.1 / -10.53; Venus 43.24 / 8.1 / 12.12;
Pluto 38.08 / 7.1 / -5.43; Mars 33.30 / 6.2 / 3.70; Jupiter 30.60 / 5.7 / 44.16;
Mercury 28.75 / 5.4 / -1.12; Neptune 18.92 / 3.5 / -6.99; Saturn 17.43 / 3.2 / 2.52.
Total 537.08 / 100.0 / 62.74.

Houses (power / % / net harmony):
11: 199.05 / 25.4 / 6.40; 12: 138.98 / 17.7 / 6.23; 1: 121.44 / 15.5 / 23.41;
5: 95.77 / 12.2 / 16.11; 10: 64.89 / 8.3 / -4.47; 3: 52.22 / 6.7 / 50.22;
2: 33.29 / 4.2 / -7.55; 7: 22.82 / 2.9 / 3.89; 4: 17.85 / 2.3 / -0.43;
9: 16.65 / 2.1 / 1.85; 8: 12.38 / 1.6 / 9.29; 6: 8.71 / 1.1 / 1.26.

Signs (power / % / net harmony):
Gemini 170.30 / 21.7 / 7.52; Leo 159.52 / 20.3 / 17.98; Cancer 129.65 / 16.5 / 10.54;
Sagittarius 95.77 / 12.2 / 16.11; Libra 71.14 / 9.1 / 43.23; Taurus 64.89 / 8.3 / -4.47;
Aquarius 22.82 / 2.9 / 3.89; Scorpio 17.85 / 2.3 / -0.43; Aries 16.65 / 2.1 / 1.85;
Virgo 14.38 / 1.8 / -0.56; Pisces 12.38 / 1.6 / 9.29; Capricorn 8.71 / 1.1 / 1.26.

Aggregations (power / % / net harmony):
- Societies: Personal 345.93 / 44.1 / 72.31; Companionship 145.15 / 18.5 / 20.83;
  Public 292.97 / 37.4 / 13.08.
- Trinities: Life 233.86 / 29.8 / 41.38; Wealth 106.89 / 13.6 / -10.76;
  Association 274.09 / 35.0 / 60.52; Psychism 169.21 / 21.6 / 15.09.
- Elements: Fire 271.94 / 34.7 / 35.95; Earth 87.97 / 11.2 / -3.77;
  Air 264.26 / 33.7 / 54.64; Water 159.88 / 20.4 / 19.40.
- Qualities: Movable 226.15 / 28.8 / 56.88; Fixed 265.07 / 33.8 / 16.97;
  Mutable 292.83 / 37.3 / 32.37.

---

## 3. Chart B - Mohandas Gandhi

Birth data: 1869-10-02, 7:12 a.m., Porbandar, India.

Planet positions (decoded from the wheel; verify against image):
- Sun 8 Libra 55; Moon 19 Leo 58; Mercury 3 Scorpio 46; Venus 16 Scorpio 26;
  Mars 18 Scorpio 23; Jupiter 20 Taurus 10 R; Saturn 12 Sagittarius 21;
  Uranus 21 Cancer 41; Neptune 18 Aries 25 R; Pluto 17 Taurus 52 R.
- Mercury is in Scorpio, so this chart does not test the disputed Mercury
  exaltation sign.

Planets (power / % / net harmony):
Moon 95.04 / 14.5 / -12.35; Mars 77.09 / 11.7 / -27.54; Jupiter 73.84 / 11.2 / 6.59;
Venus 66.80 / 10.2 / -7.14; Pluto 60.34 / 9.2 / -13.67; MC 55.54 / 8.4 / -26.60;
Asc 47.18 / 7.2 / -23.74; Uranus 46.55 / 7.1 / 16.85; Mercury 45.94 / 7.0 / -1.30;
Saturn 36.46 / 5.5 / -13.87; Neptune 36.44 / 5.5 / 5.56; Sun 16.41 / 2.5 / -5.89.
Total 657.64 / 100.0 / -103.12.

Houses (power / % / net harmony):
1: 270.40 / 27.0 / -63.30; 10: 198.10 / 19.8 / -45.14; 7: 172.73 / 17.2 / -20.85;
2: 70.82 / 7.1 / -24.17; 9: 69.52 / 6.9 / 16.20; 6: 64.01 / 6.4 / 8.60;
12: 39.38 / 3.9 / -6.55; 3: 36.92 / 3.7 / 3.29; 8: 33.40 / 3.3 / -3.57;
5: 20.75 / 2.1 / 0.75; 4: 18.23 / 1.8 / -6.93; 11: 8.21 / 0.8 / -2.95.

Signs (power / % / net harmony):
Scorpio 224.18 / 22.4 / -46.29; Taurus 167.58 / 16.7 / -10.65; Cancer 149.62 / 14.9 / -15.93;
Leo 103.24 / 10.3 / -15.30; Libra 96.99 / 9.7 / -33.21; Aries 74.98 / 7.5 / -8.21;
Sagittarius 73.38 / 7.3 / -10.57; Pisces 27.57 / 2.8 / 3.04; Gemini 22.97 / 2.3 / -0.65;
Virgo 22.97 / 2.3 / -0.65; Aquarius 20.75 / 2.1 / 0.75; Capricorn 18.23 / 1.8 / -6.93.

Aggregations (power / % / net harmony):
- Societies: Personal 417.52 / 41.6 / -90.72; Companionship 275.72 / 27.5 / -18.44;
  Public 309.23 / 30.8 / -35.45.
- Trinities: Life 360.68 / 36.0 / -46.35; Wealth 332.93 / 33.2 / -60.71;
  Association 217.85 / 21.7 / -20.51; Psychism 91.01 / 9.1 / -17.05.
- Elements: Fire 251.61 / 25.1 / -34.09; Earth 208.78 / 20.8 / -18.24;
  Air 140.71 / 14.0 / -33.11; Water 401.37 / 40.0 / -59.18.
- Qualities: Movable 339.82 / 33.9 / -64.28; Fixed 515.76 / 51.4 / -71.50;
  Mutable 146.89 / 14.7 / -8.84.

---

## 4. Chart C - Barbara Walters

Birth data: 1929-09-25, 6:50 a.m., Boston, Massachusetts.

Planet positions (decoded from the wheel; verify against image):
- Sun 1 Libra 52; Moon 23 Gemini 30; Mercury ~23 Libra; Venus 29 Leo 43;
  Mars ~22 Libra; Jupiter 16 Gemini 14; Saturn 24 Sagittarius 29;
  Uranus 9 Aries 41 R; Neptune 2 Virgo 14; Pluto 19 Cancer 29.
- Mercury is in Libra, so this chart does not test the disputed Mercury
  exaltation sign. (Mercury/Mars degrees in the wheel OCR were partly
  overlapping; verify against image.)

Planets (power / % / net harmony):
Mercury 72.19 / 14.1 / 15.72; Mars 52.50 / 10.3 / -1.58; MC 45.47 / 8.9 / -17.21;
Moon 44.88 / 8.8 / 5.45; Pluto 44.80 / 8.7 / -17.35; Saturn 43.66 / 8.5 / -14.16;
Asc 43.61 / 8.5 / -15.12; Venus 36.38 / 7.1 / 15.02; Jupiter 35.77 / 7.0 / 16.88;
Sun 33.53 / 6.5 / -8.58; Uranus 30.36 / 5.9 / -16.14; Neptune 28.87 / 5.6 / 4.52.
Total 512.04 / 100.0 / -32.56.

Houses (power / % / net harmony):
1: 186.50 / 23.8 / 6.53; 9: 116.75 / 14.9 / 30.19; 10: 112.71 / 14.4 / -31.84;
11: 82.01 / 10.5 / 15.25; 12: 69.63 / 8.9 / -0.72; 3: 61.55 / 7.8 / -5.72;
7: 56.61 / 7.2 / -16.93; 2: 24.33 / 3.1 / -4.73; 4: 21.83 / 2.8 / -7.08;
5: 18.51 / 2.4 / -7.58; 8: 18.19 / 2.3 / 7.51; 6: 16.16 / 2.1 / 5.35.

Signs (power / % / net harmony):
Libra 220.03 / 28.0 / -2.05; Gemini 116.75 / 14.9 / 30.19; Cancer 112.71 / 14.4 / -31.84;
Virgo 64.97 / 8.3 / 12.38; Sagittarius 61.55 / 7.8 / -5.72; Aries 56.61 / 7.2 / -16.93;
Leo 53.14 / 6.8 / 10.73; Scorpio 24.33 / 3.1 / -4.73; Capricorn 21.83 / 2.8 / -7.08;
Aquarius 18.51 / 2.4 / -7.58; Taurus 18.19 / 2.3 / 7.51; Pisces 16.16 / 2.1 / 5.35.

Aggregations (power / % / net harmony):
- Societies: Personal 342.00 / 43.6 / -4.65; Companionship 113.11 / 14.4 / -26.24;
  Public 329.67 / 42.0 / 21.12.
- Trinities: Life 321.75 / 41.0 / 29.14; Wealth 153.20 / 19.5 / -31.22;
  Association 200.17 / 25.5 / -7.40; Psychism 109.65 / 14.0 / -0.29.
- Elements: Fire 171.30 / 21.8 / -11.92; Earth 104.99 / 13.4 / 12.81;
  Air 355.28 / 45.3 / 20.56; Water 153.20 / 19.5 / -31.22.
- Qualities: Movable 411.18 / 52.4 / -57.90; Fixed 114.16 / 14.5 / 5.94;
  Mutable 259.43 / 33.1 / 42.20.

---

## 5. Mercury Dignity Resolution

The `Table of Essential Dignities` image is physically present in this handout
(page 3). On 2026-07-12 it was rendered directly and cross-checked against a
clearer supplied image. The Mercury row reads Aquarius 15 for exaltation, Leo
15 for fall, Scorpio for harmony, and Taurus for inharmony. This agrees with
the manual's worked Mercury-in-Aquarius calculation and closes the discrepancy.

None of the three parity charts places Mercury in Aquarius or Virgo, so they
remain neutral on this point; the direct table plus primary worked calculation
carry the evidence.

---

## 6. Verification Notes

Reviewed directly:
- the three chart reports and their six-way power checksums (all pass to rounding)
- planet positions decoded from the wheels for sign placement

Completed on 2026-07-12:
- direct digit-level confirmation against official PDF pages 9-11
- all 125 populated aspect-grid cells captured
- all planet, house, sign, summary, and chart-total rows captured
- executable three-chart engine parity within explicit named tolerances

Not performed:
- no edit to the `moira.wiki` generated copies
