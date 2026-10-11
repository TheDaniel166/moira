"""MC Maniprabha 1948 residential timing; finite selected source manifest.

The 12.15 solar-facing method is selected. 12.16 is explicitly an alternative
and is not conjoined. Entry uses the edition's Krishna-first month convention
as a named computational composition. Source tables are independent of sky
calculation and transport. Historical outcome prose is not a physical claim.
"""
from .muhurta_election import ElectionRuleContract as Rule, _manifest_digest

PROFILE = 'mc_maniprabha_1948_residential.v1'
MC48_SHA256 = 'd972964e36fff6311c2fe1be91b0be0943f58f49108451d5e18d7fef05140bde'
MC48_URL = 'https://archive.org/details/fclt-muhurta-chintamani-maniprabha-by-ramadaivagya-edit'
PURPOSES = ('foundation', 'first_entry', 'return_entry', 'old_house_entry', 'extraordinary_entry')
ENTRY = PURPOSES[1:]
DIRECTIONS = ('east', 'south', 'west', 'north')
CORNERS = ('northeast', 'southeast', 'southwest', 'northwest')
FOUNDATION_SUN = (('east', (3, 4, 9, 10)), ('west', (3, 4, 9, 10)),
                  ('north', (0, 1, 6, 7)), ('south', (0, 1, 6, 7)))
FOUNDATION_FORBIDDEN_TITHIS = (('east', tuple(range(14, 23))), ('north', tuple(range(23, 29))),
                              ('west', (29, 0, 1, 2, 3, 4)), ('south', tuple(range(5, 14))))
VRISHA_SEGMENTS = (3, 4, 4, 3, 4, 3, 4, 3)
KALASHA_SEGMENTS = (1, 4, 4, 4, 4, 4, 3, 3)
ENTRY_STARS27 = (3, 4, 11, 13, 16, 20, 25, 26)  # Rohini, Mrg, UPha, Chitra, Anu, UAsh, UBh, Rev.
EXTRA_ENTRY_STARS27 = (7, 14, 22, 23)  # Pushya, Swati, Dhanishtha, Shatabhisha.
ENTRY_MONTHS = (1, 2, 10, 11)
EXTRA_ENTRY_MONTHS = (4, 7, 8)
VAMA_RAVI = (('east', (8, 9, 10, 11, 12)), ('south', (5, 6, 7, 8, 9)),
             ('west', (2, 3, 4, 5, 6)), ('north', (11, 12, 1, 2, 3)))
ENTRY_FACING_TITHIS = (('east', (5, 10, 15)), ('south', (1, 6, 11)),
                       ('west', (2, 7, 12)), ('north', (3, 8, 13)))
# Zero-based sidereal sign -> corner of first residential excavation, 12.19.
EXCAVATION_CORNERS = ('northwest', 'southwest', 'southwest', 'southwest',
                      'southeast', 'southeast', 'southeast', 'northeast',
                      'northeast', 'northeast', 'northwest', 'northwest')

RULES = (
    Rule('vastu.foundation_vrisha', 'MC48 12.13-14; PDF348-349',
         'inclusive Sun28 to Moon28 ordinal8..18; unequal Abhijit astronomical adapter',
         ('foundation',), ('Sun', 'Moon'), ('Sun28', 'Moon28'), 'verse_with_named_28_star_composition'),
    Rule('vastu.foundation_sun_facing', 'MC48 12.15; PDF349-350',
         'declared E/W or N/S facing selects four permitted sidereal solar signs',
         ('foundation',), ('Sun', 'facing'), ('Sun_sign',)),
    Rule('vastu.foundation_facing_tithi', 'MC48 12.17; PDF351-352',
         'four facing-specific forbidden sectors partition the30 absolute tithis',
         ('foundation',), ('Sun', 'Moon', 'facing'), ('tithi',)),
    Rule('vastu.foundation_panchanga', 'MC48 12.18 Maniprabha commentary; PDF352',
         'no Sun/Tue; no1/4/8/9/14 or new Moon; no final five stars; no movable Lagna',
         ('foundation',), ('Sun', 'Moon', 'solar', 'Lagna'), ('tithi', 'Moon27', 'sunrise', 'Lagna_sign')),
    Rule('vastu.foundation_placements', 'MC48 12.18; PDF352',
         'seven-classical composition: each benefic outside8/12; each malefic in3/6/11',
         ('foundation',), ('seven_planets', 'Lagna'), ('planet_signs', 'Lagna_sign', 'Moon_phase'), 'named_seven_graha_placement_reading'),
    Rule('vastu.excavation_corner', 'MC48 12.19; PDF353',
         'declared actual first-excavation corner equals source residential recommendation',
         ('foundation',), ('Sun', 'excavation_corner'), ('Sun_sign',)),
    Rule('vastu.entry_calendar', 'MC48 13.1-2,4; PDF359-361;12.16 month commentary',
         'Purnimanta named-month selection; ordinary sidereal Uttarayana; explicit13.2 exceptions',
         ENTRY, ('Sun', 'lunar_month'), ('Sun_sign', 'lunar_month'), 'named_purnimanta_entry_composition'),
    Rule('vastu.entry_star', 'MC48 13.1-2 with11.36; PDF297-298,359-360',
         'eight Dhruva/Mrdu stars, named additions; conjunctive own-facing seven-of28 qualification',
         ENTRY, ('Moon', 'facing'), ('Moon27', 'Moon28'), 'commentarial_conjunctive_facing_reading'),
    Rule('vastu.entry_lagna', 'MC48 13.1,4; PDF359-361',
         'fixed OR upachaya from natal Moon/Lagna; never movable; natal qualifications in personal layer',
         ENTRY, ('Lagna', 'participant'), ('Lagna_sign',)),
    Rule('vastu.entry_panchanga', 'MC48 13.4; PDF360-361',
         'no Sunday/Tuesday; no Rikta or Amavasya',
         ENTRY, ('Sun', 'Moon', 'solar'), ('tithi', 'sunrise')),
    Rule('vastu.entry_placements', 'MC48 13.3-4; PDF360-361',
         'seven-classical composition: empty4/8; benefics1/2/3/4/5/7/9/10/11; malefics3/6/11',
         ENTRY, ('seven_planets', 'Lagna'), ('planet_signs', 'Lagna_sign', 'Moon_phase'), 'named_seven_graha_placement_reading'),
    Rule('vastu.entry_vama_ravi', 'MC48 13.5; PDF363-364',
         'front-door direction selects five Sun houses from election Lagna',
         ENTRY, ('Sun', 'Lagna', 'facing'), ('Sun_sign', 'Lagna_sign')),
    Rule('vastu.entry_facing_tithi', 'MC48 13.5; PDF364',
         'E Purna; S Nanda; W Bhadra; N Jaya; separate new-Moon prohibition retained',
         ENTRY, ('Sun', 'Moon', 'facing'), ('tithi',)),
    Rule('vastu.entry_kalasha', 'MC48 13.6; PDF364-365',
         'inclusive Sun27 to Moon27 ordinals6..13 or22..27',
         ENTRY, ('Sun', 'Moon'), ('Sun27', 'Moon27')),
    Rule('vastu.entry_availability', 'MC48 13.2 contrast with ordinary entry; SS IX adapter',
         'Jupiter and Venus between certified appearance/disappearance; no marriage waiting buffers',
         ENTRY, ('Jupiter_apparition', 'Venus_apparition'), ('apparitions',), 'named_SS_asta_composition'),
    Rule('vastu.personal_entry', 'MC48 13.1,4; PDF359-361',
         'natal eighth exclusion and named natal-Moon/election-Moon2/12,5/9,6/8 Bhakuta composition',
         ENTRY, ('Sun', 'Moon', 'Lagna', 'participant'), ('Moon_sign', 'Lagna_sign'), 'named_resident_bhakuta_composition'),
)
EXCLUSIONS = (
    ('architecture', 'MC12.1-12 site/name/area calculations and12.20-28 design/longevity testimony are outside this timing profile'),
    ('alternate_construction_calendar', 'MC12.16 is a separately described alternative; this profile selects12.15 solar-facing method'),
    ('door_installation', 'MC12.29 is a separate elected action'),
    ('preparatory_worship', 'MC13.3 worship and13.7 ritual acts have their own anchors and are not verified by an ephemeris'),
    ('structural_safety', 'source timing does not establish structural safety or certify a dwelling'),
    ('other_editions', 'KP contradictions and other Vastu traditions do not alter the selected MC48 readings'),
    ('node_placement_extension', 'selected placement composition uses seven classical grahas; imposing both opposite nodes in3/6/11 is unsatisfiable'),
)
MANIFEST_SHA256 = _manifest_digest((PROFILE, MC48_SHA256, RULES, EXCLUSIONS,
    FOUNDATION_SUN, FOUNDATION_FORBIDDEN_TITHIS, VRISHA_SEGMENTS, KALASHA_SEGMENTS,
    ENTRY_STARS27, EXTRA_ENTRY_STARS27, ENTRY_MONTHS, EXTRA_ENTRY_MONTHS,
    VAMA_RAVI, ENTRY_FACING_TITHIS, EXCAVATION_CORNERS))
