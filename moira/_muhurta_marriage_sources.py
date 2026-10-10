"""Edition-owned marriage tables, independently collated from primary scans.

Authority: Rama Daivajna, Muhurta Chintamani, Ramlal Avasthi Hindi
commentary, 2004. PDF SHA256 below identifies the inspected edition. Verse,
commentary and modern composition decisions are distinguished in the standard.
Numbers below are zero-based signs/stars, except explicitly inclusive counts.
No mutable legacy activity dictionary owns these tables.
"""
from dataclasses import dataclass

MC_SHA256 = '9e931eb7fdc1958516424590a168680be60753f4cfccea8f327cae973dfe4777'
MC_URL = 'https://archive.org/details/muhurta-chintamani-hindi'
ORDINARY = 'mc_avasthi_2004_marriage_ordinary.v1'
PERSONAL = 'mc_avasthi_2004_marriage_personal.v1'
GODHULI = 'vv_half_ghati_mc_99_101_marriage_godhuli.v1'
VISIBILITY = 'ss_ix_modern_apparent_diurnal_arc.v1'

SEVEN = ('Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn')
NINE = SEVEN + ('Rahu', 'Ketu')
STARS = ('Ashwini', 'Bharani', 'Krittika', 'Rohini', 'Mrigashira', 'Ardra',
         'Punarvasu', 'Pushya', 'Ashlesha', 'Magha', 'PurvaPhalguni',
         'UttaraPhalguni', 'Hasta', 'Chitra', 'Swati', 'Vishakha', 'Anuradha',
         'Jyeshtha', 'Mula', 'PurvaAshadha', 'UttaraAshadha', 'Shravana',
         'Dhanishtha', 'Shatabhisha', 'PurvaBhadrapada', 'UttaraBhadrapada', 'Revati')
STARS28 = STARS[:21] + ('Abhijit',) + STARS[21:]
WEDDING_STARS = (3, 4, 9, 11, 12, 14, 16, 18, 20, 25, 26)  # Vivaha 55
WEEKDAYS = (1, 3, 4, 5)  # Sunday=0; Vivaha 55
FORBIDDEN_PAKSHA_TITHIS = (4, 6, 8, 9, 12, 14)  # Shubhashubha 36 + Vivaha 55
ALLOWED_TITHI_INDICES = tuple(i for i in range(30)
                            if i % 15 + 1 not in FORBIDDEN_PAKSHA_TITHIS and i != 29)
FIVE_LINE_PAIRS = ((3, 21), (1, 16), (20, 4), (22, 9), (12, 26),
                   (14, 24), (18, 6), (11, 27))  # 28-star identities, Vivaha 56
SEVEN_LINE_PAIRS = ((17, 7), (24, 14), (19, 5), (27, 11), (23, 15),
                    (20, 4), (0, 10), (8, 16), (12, 26), (3, 21),
                    (18, 6), (13, 25), (1, 9), (2, 22))  # Vivaha 57
# Inclusive count includes occupied star. Rahu direction is the explicit
# Avasthi commentary reversal (Ashwini -> Ashlesha), NOT a general speed rule.
LATTA = (('Sun', 12, 1), ('Saturn', 8, 1), ('Jupiter', 6, 1), ('Mars', 3, 1),
         ('Mercury', 7, -1), ('Rahu', 9, 1), ('Moon', 22, -1), ('Venus', 5, -1))
KRANTISAMYA = ((4, 0), (1, 9), (6, 10), (5, 11), (3, 7), (8, 2))
PATA_YOGAS = (13, 26, 21, 16, 9, 8)  # Harshana, Vaidhriti, Sadhya, Vyatipata, Ganda, Shula
EKARGALA_YOGAS = (12, 9, 16, 0, 8, 26, 14, 18, 5)
UPAGRAHA_COUNTS = (5, 8, 10, 14, 7, 19, 15, 18, 21, 22, 23, 24, 25)
DAY_EIGHTHS = (4, 7, 2, 5, 8, 3, 6)
KULIKA_DAY = (14, 12, 10, 8, 6, 4, 2)
KULIKA_NIGHT = (13, 11, 9, 7, 5, 3, 1)
# Vivaha52-54: each full day/night has its own fifteen named deities.
# Applying verse54 to BOTH lists preserves the often-abridged night clauses.
DURMUHURTA_DAY = ((14,), (9,12), (4,), (8,), (6,12), (4,9), (1,2))
DURMUHURTA_NIGHT = ((), (8,), (7,), (), (), (8,), (1,))
DAGDHA = (6, 4, 8, 6, 10, 8, 12, 10, 2, 12, 4, 2)
DASHAYOGA_REMAINDERS = (0, 1, 4, 6, 10, 11, 15, 18, 19, 20)
SOUTHERN_BANA = ((8, 'illness'), (2, 'fire'), (4, 'royal'), (6, 'theft'), (1, 'death'))
SOLAR_BANA = ((6, 'illness'), (3, 'fire'), (1, 'royal'), (8, 'theft'), (4, 'death'))
# MC80 Sanskrit number words and explicit commentary total BEFORE+AFTER.
# Symmetric halves are a named Moira convention, not a statement in the verse.
INGRESS_TOTAL_GHATIS = (('Sun', 33), ('Moon', 2), ('Mars', 9), ('Mercury', 6),
                       ('Jupiter', 88), ('Venus', 9), ('Saturn', 160))
DAY_DEFECTS = (('deaf', (6, 7)), ('blind', (4, 0, 1)), ('lame', (10,)))
NIGHT_DEFECTS = (('deaf', (9, 8)), ('blind', (5, 2, 3)), ('lame', (11,)))
SOLAR_MARRIAGE_SIGNS = (0, 1, 2, 7, 9, 10)
# Ordinary amanta physical lunations; derived table from Vivaha13's six solar
# signs and explicit Chaitra/Kartika/Pausha/Ashadha qualifications. Not a quote
# of twelve enumerated lunar months in the verse. Ashadha also needs Shukla1-10.
MARRIAGE_MONTH_SIGNS = ((0,), (0,1), (1,2), (2,), (), (), (), (7,), (7,), (9,), (9,10), (10,))


@dataclass(frozen=True, slots=True)
class MarriageRuleDefinition:
    """One required family and its finite dependency/source contract."""
    rule_id: str
    finding_id: str
    locus: str
    layer: str
    dependencies: tuple[str, ...]
    applicability: str = 'required'


def _rule(rule, finding, locus, dependencies, layer='astronomical', applicability='required'):
    return MarriageRuleDefinition(rule, finding, 'MC Avasthi 2004, ' + locus,
                                  layer, tuple(dependencies.split()), applicability)


RULES = (
    _rule('wedding_star', 'M02', 'Vivaha 55', 'moon.star27'),
    _rule('wedding_tithi', 'M02', 'Vivaha 55; Shubhashubha 36', 'sun.moon.phase'),
    _rule('wedding_weekday', 'M02', 'Vivaha 55', 'solar.sunrise_weekday'),
    _rule('wedding_karana', 'M03', 'Shubhashubha 34', 'sun.moon.phase'),
    _rule('calendar', 'M04', 'Vivaha 13; Samskara 26', 'sun.sign lunar_month tithi'),
    _rule('five_line_vedha', 'M05', 'Vivaha 56', 'all.star28 all.pada'),
    _rule('seven_line_vedha', 'M06', 'Vivaha 57', 'all.star28 all.pada nature'),
    _rule('star_history', 'M07', 'Vivaha 58', 'planet.star_history moon.star_history'),
    _rule('latta', 'M08', 'Vivaha 59/64 commentary', 'region all.star27 all.pada moon.phase', applicability='regional'),
    _rule('pata', 'M09', 'Vivaha 60/64', 'region yoga.ending_star sun.pada moon.pada', applicability='regional'),
    _rule('krantisamya', 'M10', 'Vivaha 61', 'sun.sign moon.sign'),
    _rule('ekargala', 'M11', 'Vivaha 62', 'sun.star28 moon.star28 yoga'),
    _rule('upagraha', 'M12', 'Vivaha 63/64', 'region sun.star27 moon.star27 sun.pada moon.pada', applicability='regional'),
    _rule('day_eighth', 'M13', 'Vivaha 64', 'solar.day solar.weekday'),
    _rule('kulika', 'M14', 'Vivaha 65', 'solar.day solar.night solar.weekday'),
    _rule('dagdha', 'M15', 'Vivaha 66', 'sun.sign tithi'),
    _rule('jamitra', 'M16', 'Vivaha 67/68', 'lagna moon all.sign all.navamsa'),
    _rule('dashayoga', 'M17', 'Vivaha 69-71', 'region sun.star27 moon.star27 all.star28 lagna aspects'),
    _rule('southern_bana', 'M18', 'Vivaha 72', 'region tithi lagna.sign', applicability='regional'),
    _rule('solar_bana', 'M19', 'Vivaha 73/74', 'sun.whole_degree solar.day solar.weekday'),
    _rule('lagna_components', 'M20', 'Vivaha 75-78,84-88,92', 'lagna all.sign all.navamsa nature combustion'),
    _rule('solar_ingress', 'M21', 'Vivaha 79', 'sun.ingress solar.sunrise'),
    _rule('planetary_ingress', 'M21', 'Vivaha 80', 'all.sign_ingress'),
    _rule('lagna_day_night', 'M21', 'Vivaha 81/83', 'lagna.sign solar.day aspects'),
    _rule('kartari', 'M22', 'Vivaha 44/88', 'lagna.sign moon.sign all.sign all.motion nature dignity combustion'),
    _rule('broad_remedies', 'M22', 'Vivaha 89-91', 'lagna all.sign all.navamsa', applicability='remedy'),
    _rule('jupiter_availability', 'M23', 'Samskara 27; SS IX.2-11 modern extension', 'jupiter.apparition_history'),
    _rule('venus_availability', 'M23', 'Samskara 27; SS IX.2-11 modern extension', 'venus.apparition_history'),
    _rule('personal_shuddhi', 'M24', 'Vivaha 12', 'personal.roles natal.moon sun.sign moon.sign jupiter.sign', layer='personal'),
    _rule('birth_period', 'M25', 'Vivaha 14-15', 'personal.birth_month personal.birth_tithi personal.first_born natal.star natal.lagna', layer='personal'),
    _rule('personal_tara', 'M26', 'Gochara 13; Vivaha Janma commentary', 'natal.star moon.star moon.pada', layer='personal'),
    _rule('marriage_context', 'M27', 'Vivaha 93-95', 'personal.context', layer='personal'),
    _rule('godhuli', 'M28', 'Vivaha 99-101; VV half-ghati geometry', 'solar.half_set solar.weekday moon.sign mars.sign lagna', layer='composition'),
    _rule('nitya_yoga', 'F01', 'Shubhashubha 34/35', 'sun.moon.yoga yoga.parent'),
    _rule('vishanadi', 'F02', 'Vivaha 49-51', 'moon.star27 nakshatra.parent'),
    _rule('yamaghanta_yoga', 'F03', 'Shubhashubha 9', 'moon.star27 solar.weekday'),
    _rule('yamaghanta_kala', 'F04', 'Shubhashubha 37 commentary', 'solar.day solar.weekday'),
    _rule('nakshatra_gandanta', 'F05', 'Vivaha 43', 'nakshatra.parent'),
    _rule('tithi_gandanta', 'F06', 'Vivaha 43', 'tithi.parent'),
    _rule('lagna_gandanta', 'F07', 'Vivaha 43', 'lagna.parent'),
    _rule('tithi_sunrise_count', 'F08', 'Shubhashubha 34', 'tithi.parent solar.sunrise_history'),
    _rule('durmuhurta', 'F09', 'Vivaha 52-54', 'solar.day solar.night solar.weekday'),
)

EXCLUSIONS = (
    ('compatibility_matching', 'Vivaha 21 onward: natal compatibility is a separate product'),
    ('historical_social_prescriptions', 'Age, kinship and social status are not numerical eligibility'),
    ('family_ritual_spacing', 'Vivaha 15-16 kinship/ceremony-spacing clauses are outside the anchor election; the Vivaha15 Jyeshtha/firstborn clause is admitted'),
    ('shraddha_and_death_anniversaries', 'Caller ritual obligations are outside the selected astronomical and birth-context profile'),
    ('mc93_relatives_predictions', 'Strength-based predictions supply no ordinary timing veto'),
    ('mc94_social_class_variant', 'Historical class-specific permissions are not the selected ordinary profile'),
    ('mc95_special_marriage_forms', 'Tripadi for special historical forms is not ordinary marriage'),
    ('ritual_donation_performance', 'Gochara13 trijanma donation is not inferred or performed by an astronomical engine'),
    ('preparatory_acts', 'Vivaha 96-98: separate preparatory ceremonies'),
    ('extraordinary_omens', 'Vivaha 58/89: weather and non-ephemeris omens'),
    ('necessary_activity_tithi_relief', 'Shubhashubha 36: ordinary marriage does not invoke necessity'),
    ('mc82_alternative_lagna', 'Avasthi explicitly reports no authority for the alternative'),
    ('mc91_numeric_dosha_subtraction', 'No source defines weights for arbitrary implementation rows'),
    ('physical_visibility', 'SS time-degrees do not model atmosphere or observed first visibility'),
    ('whole_ceremony_duration', 'Elects a declared ritual anchor only'),
)

RESEARCH_VARIANTS = (
    ('kp_marriage', 'research_only'), ('raman_marriage', 'research_only'),
    ('pvr_marriage', 'research_only'), ('bs_marriage', 'research_only'),
    ('mc82_alternative_lagna', 'not_admitted'),
    ('mc28_urgent_waiting_periods', 'not_admitted'),
)
