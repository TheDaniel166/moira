"""MC48 ordinary land departure: finite source and cross-reference admission.

The closing synopsis is the conservative precedence chosen here. Regional
Ghata/Mahadala tables and royal/war permissions are not ordinary permissions.
MC04 general detectors are explicitly imported compositions, not an assertion
that the two commentaries have identical clocks (Vishanadi demonstrably differs).
"""
from .muhurta_election import ElectionRuleContract as Rule, _manifest_digest
from ._muhurta_marriage_sources import RULES as MC04_RULES

PROFILE = 'mc_maniprabha_1948_ordinary_land.v1'
SHA256 = 'd972964e36fff6311c2fe1be91b0be0943f58f49108451d5e18d7fef05140bde'
URL = 'https://archive.org/details/fclt-muhurta-chintamani-maniprabha-by-ramadaivagya-edit'
MC04_SHA256 = '9e931eb7fdc1958516424590a168680be60753f4cfccea8f327cae973dfe4777'
BEST_STARS = (0, 6, 16, 4, 7, 26, 12, 21, 22)
MIDDLE_STARS = (11, 20, 25, 23, 18, 17, 10, 19, 24, 3)
STAR_SHULA = (17, 24, 3, 11)  # east, south, west, north
DAY_SHULA = ((1, 6), (4,), (0, 5), (2, 3))
PARIGHA_RELIEF = (16, 12, 7, 0)
YOGINI = ((1, 9), (3, 11), (5, 13), (4, 12), (6, 14), (7, 15), (2, 10), (8, 30))
DIRECTION_LORDS = ('Sun', 'Venus', 'Mars', 'Rahu', 'Saturn', 'Moon', 'Mercury', 'Jupiter')
IMPORT_FAMILIES = (
    'wedding_karana', 'five_line_vedha', 'seven_line_vedha', 'star_history',
    'krantisamya', 'ekargala', 'day_eighth', 'kulika', 'dagdha', 'jamitra',
    'solar_bana', 'solar_ingress', 'planetary_ingress', 'lagna_day_night',
    'kartari', 'nitya_yoga', 'vishanadi', 'yamaghanta_yoga', 'yamaghanta_kala',
    'nakshatra_gandanta', 'tithi_gandanta', 'lagna_gandanta',
    'tithi_sunrise_count', 'durmuhurta', 'lagna_components',
)


def rule(name, locus, formula, dependencies, transitions, attribution='verse_and_selected_commentary'):
    return Rule('travel.mc_' + name, 'MC48 Yatra ' + locus, formula, ('departure',),
                tuple(dependencies.split()), tuple(transitions.split()), attribution)


RULES = (
    rule('star', '9/PDF279-280', 'nine best and ten middling admitted; eight adverse excluded', 'Moon', 'Moon27'),
    rule('solar_grade', '8/PDF278', 'solar sign quality is retained as advisory', 'Sun', 'Sun_sign'),
    rule('tithi', '9/PDF279;1.4', 'reject6/12/8/Rikta,Shukla1,full/new; Siddha weekday exception targets only this row', 'Sun Moon solar', 'tithi sunrise'),
    rule('weekday', '111/PDF333-334', 'closing synopsis Sun/Tue/Sat prohibition takes precedence over9 commentary', 'solar', 'sunrise', 'explicit_closing_synopsis_precedence'),
    rule('direction_shula', '10/37/PDF280-281,299', 'source cardinal star/weekday; intercardinal uses preceding cardinal clockwise', 'Moon solar direction', 'Moon27 sunrise'),
    rule('time_star', '11/110/PDF283,333', 'day/night thirds; Shravana/Hasta/Pushya/Mrigashira exempt', 'Moon solar', 'Moon27 sunrise sunset parent_thirds'),
    rule('rahu_half', '14/111', 'Rahu occupied star excluded; following13 Jiva, preceding13 Mrita; inclusive2..14 admitted', 'Moon Rahu', 'Moon27 Rahu27'),
    rule('three_moduli', '24/PDF291', 'one-based tithi+star+weekday; independent mod7/8/3 must be nonzero', 'Sun Moon solar', 'tithi Moon27 sunrise', 'month_1_to_30_ordinal_composition'),
    rule('yogini', '34/PDF296', 'avoid Yogini in front or90degrees left; new Moon30 differs from fullMoon15', 'Sun Moon direction', 'tithi'),
    rule('kala_pasha', '35/PDF297', 'Sunday north then anticlockwise per weekday; reverse at night; avoid facing Kala or opposite Pasha', 'solar direction', 'sunrise sunset'),
    rule('parigha', '36-38/PDF297-300', 'Krittika-first four groups of seven28-stars; own directional group; four universal relief stars', 'Moon direction', 'Moon28'),
    rule('ayana', '39/PDF300', 'north/east when both Uttara; south/west when both Dakshina; otherwise Sun day/Moon night', 'Sun Moon solar direction', 'Sun_sign Moon_sign sunrise sunset', 'sidereal_sign_ayana_composition'),
    rule('venus_facing', '40-42/PDF301-302', 'solar-relative east/west;42 MoonRevati throughKrittika firstpada relieves ONLY facing', 'Sun Venus Moon direction', 'Venus_minus_Sun_0_180 Moon108', 'first_of_three_direction_conventions_and_first_blind_Venus_reading'),
    rule('venus_state', '41-42/110/PDF301-302,333', 'retain retrograde/debilitated/asta; royal blind-Venus and Mercury-war relief excluded', 'Venus apparition', 'Venus_sign Venus_station apparition', 'SS_geometry_without_marriage_waiting_periods'),
    rule('lagna', '43-47/112/PDF303-304,334;Brihat Jataka1.10', 'noAquarius/PiscesD1/D9;44 qualifies Pisces under both benefic natal lords and natal sign; no back-risingD1; no opposite-directionD1', 'Lagna natal planets direction', 'Lagna108 planet_sign Moon_phase'),
    rule('retrograde', '38/112/PDF300,334', 'five nonluminary classical planets: no retrograde in Kendra, its D1/D9 lordship in Lagna, or its weekday', 'five_planets Lagna solar', 'planet_station planet_sign Lagna108 sunrise', 'D1_D9_selected_varga_scope'),
    rule('placements', '49-50/111-112', 'noSaturn10/Venus7; directionlordKendra advisory; Moon left/back prohibited by sign-direction composition', 'planets Lagna direction', 'planet_sign Lagna_sign', 'sign_direction_composition'),
    rule('southern', '111/PDF333-334', 'south and southeast exclude finalfive stars and Abhijit DAY MUHURTA', 'Moon solar direction', 'Moon27 sunrise sunset day_fifteenth'),
    rule('personal', '8/45/PDF278,303-304', 'natal Moon Tara3/5/7; eighth from natal Moon/Lagna and their eighth-lords in Lagna', 'natal Moon Lagna planets', 'Moon27 Moon_sign Lagna_sign planet_sign'),
    rule('prior_departure', '92-95/PDF323-325', 'declared prior act is contextual; five nights at one stop requires a fresh election; current act always assessed', 'declared_context', 'none', 'no_inherited_or_retroactive_clearance'),
)
EXCLUSIONS = (
    ('scope', 'ordinary land departure only; return means return-leg departure, not home arrival11.109'),
    ('regional_25_33', 'MC48 PDF295 explicitly calls Mahadala/Ghata regional; nonregional composition omits25-33 despite synopsis mention'),
    ('rahu_example_conflict', '11.14/PDF285 printed Svati-to-Revati example is one star short; selected explicit13+occupied1+13 verse partition, not erroneous example endpoints'),
    ('royal_war', '11.15-23,48,51-75,80-81 royal/war outcomes and same-day royal relief are not ordinary permissions'),
    ('necessary_star_relief', '11.12-13 and37 necessary-journey alternatives are outside this ordinary profile'),
    ('water_transport', '11.46 boat-specific water-sign reading includingCapricorn/Aquarius requires its own profile'),
    ('venus_alternatives', '11.40 northern/southern and28-star directions remain alternatives, not silently conjoined'),
    ('wedding_preferences', '11.112 imports defects, not wedding calendar/star/weekday/Navamsa preferences, partner rules, placement score, Godhuli or Samskara waiting periods'),
    ('regional_marriage_imports', 'latta,pata,upagraha,dashayoga,southern_bana require separate regional admission'),
    ('marriage_remedies', 'no blanket wedding remedy graph imported; source-specific travel Siddha and Parigha targets only'),
    ('ritual_weather_omens', '11.76-79,83-108 physical ritual, weather and omen facts are outside ephemeris eligibility'),
    ('departure_measurements', 'residence/room/boundary anchors are declared actual acts; no invented dhanus-to-km conversion or proof of performance'),
    ('prior_election_inheritance', 'earlier act never rescues current adverse timing;5nights is one-stop duration, not total journey age'),
    ('outcome_prose', 'no prediction of harm, victory, illness or physical travel safety'),
)
IMPORTED_RULES=tuple(Rule('travel.mc_import.'+r.rule_id,
    'MC48 Yatra11.112; explicit MC04 detector composition: '+r.locus,
    'admitted defect detector; no wedding preferences or remedy graph'+
    ('; MC48 BOTH Vishanadi start and width proportional' if r.rule_id=='vishanadi' else ''),
    ('departure',),r.dependencies,('canonical108_and_phase_roots','motion_roots','history_roots','derived_parent_edges'),
    'named_cross_edition_composition') for r in MC04_RULES if r.rule_id in IMPORT_FAMILIES)
RULES=RULES+IMPORTED_RULES
MANIFEST_SHA256 = _manifest_digest((PROFILE,SHA256,MC04_SHA256,BEST_STARS,MIDDLE_STARS,STAR_SHULA,
    DAY_SHULA,PARIGHA_RELIEF,YOGINI,DIRECTION_LORDS,IMPORT_FAMILIES,RULES,EXCLUSIONS))
