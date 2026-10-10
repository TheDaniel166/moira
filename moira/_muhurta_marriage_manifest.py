"""Finite source/formula/transport compatibility manifest for VED-011."""
from dataclasses import dataclass

from ._muhurta_marriage_sources import RULES,MC_SHA256,MC_URL,GODHULI

TARGETS68=frozenset(('ekargala','upagraha','pata','latta','jamitra','kartari'))
TARGETS89=frozenset(('wedding_tithi','calendar','dagdha','lagna_day_night','tithi_sunrise_count','star_history'))
TARGETS_BROAD=TARGETS68|TARGETS89|frozenset(('wedding_star','wedding_weekday','wedding_karana',
 'five_line_vedha','seven_line_vedha','krantisamya','dashayoga','southern_bana','solar_bana',
 'day_eighth','kulika','durmuhurta','lagna_components','solar_ingress','planetary_ingress',
 'nitya_yoga','vishanadi','yamaghanta_yoga','yamaghanta_kala','nakshatra_gandanta','tithi_gandanta','lagna_gandanta'))
GODHULI_TARGETS=TARGETS_BROAD-frozenset(('calendar','solar_ingress','planetary_ingress'))


@dataclass(frozen=True,slots=True)
class MarriageRemedyContract:
    """Source locus, exact target set and prerequisite for one named remedy."""
    remedy_id: str
    locus: str
    family_targets: tuple[str,...]
    rule_targets: tuple[str,...]
    qualification: str
    selection: str = 'policy_remedies'


REMEDY_CONTRACTS=(
 MarriageRemedyContract('mc71_empty_opposition_or_benefic_lagna','MC Vivaha71 and attributed Vyasa remedy',
    ('dashayoga',),(),'empty opposing star OR Jupiter/Venus placement or aspect to Lagna','intrinsic_rule'),
 MarriageRemedyContract('mc68_own_or_exalted_luminaries','MC Vivaha68',tuple(sorted(TARGETS68)),
    ('lagna_components.lagna_support','lagna_components.seventh_support'),'both luminaries own or exalted; finite strength interpretation'),
 MarriageRemedyContract('mc83_lagna_aspect','MC Vivaha83',('lagna_day_night',),(),
    'Lagna lord OR Jupiter has a source-admitted sign aspect to Lagna'),
 MarriageRemedyContract('mc88_weak_afflictors','MC Vivaha88',('kartari',),
    ('lagna_components.venus_house_6','lagna_components.mars_house_8','lagna_components.moon_house_6',
     'lagna_components.moon_house_8','lagna_components.moon_house_12'),
    'component-specific debility/enemy/orb criteria; both Kartari afflictors independently weak'),
 MarriageRemedyContract('mc89_benefic_kendra_trikona','MC Vivaha89',tuple(sorted(TARGETS89)),(),
    'Mercury OR Jupiter OR Venus in1/4/5/9/10 from Lagna'),
 MarriageRemedyContract('mc90_anvaya_disjunction','MC Vivaha90',tuple(sorted(TARGETS_BROAD)),(),
    'Jupiter1/4/5/9/10 OR Sun11 OR Lagna vargottama OR Moon vargottama'),
 MarriageRemedyContract('mc90_moon_eleventh','MC Vivaha90',('durmuhurta',),('lagna_components.navamsa_allowed_sign',),
    'Moon11; Navamsa target additionally requires Sun/Mars/Saturn-owned Lagna D9; no last/movable cancellation'),
 MarriageRemedyContract('mc91_lagna_lords_placement','MC Vivaha91',tuple(sorted(TARGETS_BROAD)),(),
    'Lagna OR Lagna-Navamsa lord in1/4/10/11; capacities100/200/100000 advisory, never row subtraction'),
 MarriageRemedyContract(GODHULI,'MC Vivaha99-101 with VV temporal composition',tuple(sorted(GODHULI_TARGETS)),(),
    'inside weekday-qualified window; Moon not1/6/8 and Mars not1/7/8; ordinary findings retained','godhuli_flag'),
)


@dataclass(frozen=True,slots=True)
class MarriageRuleContract:
    """Finite rule-family contract linking source coverage, inputs, transitions and transport."""
    family_id: str
    inventory_id: str
    authority: str
    attribution: str
    formula: str
    clock_and_partition: str
    transition_dependencies: tuple[str,...]
    missing_input_behavior: str
    fixture_references: tuple[str,...]
    transport_fields: tuple[str,...]
    permitted_exception_ids: tuple[str,...]
    component_profiles: tuple[str,...]


# Formula descriptions identify the actual finite calculation, including
# named modern compositions where the verse does not specify an algorithm.
_FORMULAS={
 'wedding_star':'Moon27 in the eleven WEDDING_STARS, including Mula',
 'wedding_tithi':'paksha tithi4/6/8/9/12/14 and Krishna15 prohibited',
 'wedding_weekday':'sunrise-owned weekday in Monday/Wednesday/Thursday/Friday',
 'wedding_karana':'Vishti prohibited; no MC Kinstughna veto established',
 'calendar':'MARRIAGE_MONTH_SIGNS with ordinary amanta month; Ashadha Gemini Shukla1..10; Vivaha13 precedence',
 'five_line_vedha':'eight FIVE_LINE_PAIRS, reciprocal28-star identity, opposing physical pada',
 'seven_line_vedha':'fourteen SEVEN_LINE_PAIRS; malefic whole-star or benefic opposing-pada qualification',
 'star_history':'nearest previous/current/next27-star distinct-afflictor occupancy; event-time Mercury nature; persistent28-star piercing until complete lunar traversal',
 'latta':'LATTA inclusive27-star offsets with source direction; regional applicability; no retrograde reversal',
 'pata':'selected PATA_YOGAS ending in current complete Moon27 occurrence with solar-pada qualification',
 'krantisamya':'six reciprocal KRANTISAMYA_PAIRS of solar/lunar signs',
 'ekargala':'selected EKARGALA_YOGAS and odd inclusive Sun28-to-Moon28 count',
 'upagraha':'selected UPAGRAHA_COUNTS inclusive27-star Sun-to-Moon distance and same-pada qualification',
 'day_eighth':'DAY_EIGHTHS weekday ordinal of complete daylight parent',
 'kulika':'KULIKA_DAY and KULIKA_NIGHT fifteenths; Saturday additional final night fifteenth',
 'dagdha':'DAGDHA paksha tithi selected by sidereal Sun sign',
 'jamitra':'any planet seventh sign or physical108-navamsa delta54 from Lagna or Moon',
 'dashayoga':'(Sun27 ordinal+Moon27 ordinal)%27, selected residues,28-star opposition; residue10 special pair',
 'southern_bana':'Dakshinatya only: (elapsed absolute tithi+one-based Lagna)%9; residues8/2/4/6/1',
 'solar_bana':'(floor(Sun degree within sign)+6/3/1/8/4)%9==5; source weekday and day/night scopes',
 'lagna_components':'canonical MC75-78/84-88 placements, support, Navamsa, targeted afflictions; MC92 total<5 prohibition and overlapping advisory bands',
 'solar_ingress':'cardinal ingress sunrise-owned date plus adjacent solar dates; other ingresses +/-16ghati',
 'planetary_ingress':'INGRESS_TOTAL_GHATIS split symmetrically before/after actual directional sign crossings',
 'lagna_day_night':'DAY_DEFECTS/NIGHT_DEFECTS; optional Lagna-lord OR Jupiter aspect remedy',
 'kartari':'direct malefic12th AND retrograde malefic2nd from Lagna/Moon; each afflictor separately qualified for MC88',
 'broad_remedies':'finite MC68/83/88/89/90/91 target sets; raw restrictions retained; no arbitrary dosha-point subtraction',
 'jupiter_availability':'SS-derived east appearance11/west disappearance11 time-degrees; elapsed UT1 buffers15/15',
 'venus_availability':'SS-derived east appearance8/disappearance10, west appearance10/disappearance8; buffers3/15 and10/5',
 'personal_shuddhi':'bride Jupiter2/5/7/9/11; groom Sun3/6/10/11; both Moons exclude1/4/8/12 from own natal Moon',
 'birth_period':'firstborn birth month/star/tithi/Lagna predicates; triple-Jyeshtha restriction and double-Jyeshtha advisory',
 'personal_tara':'election Tara cycle, MC Sanskrit second-cycle quarters; firstborn Janma override, unremedied10/19 trijanma',
 'marriage_context':'MC93 predictions, MC94 historical social variant and MC95 special forms explicitly outside ordinary timing',
 'godhuli':'VV +/-half-ghati around solar center -34arcmin; Thursday after/Saturday before full setting -50arcmin; retained Moon/Mars qualifications',
 'nitya_yoga':'canonical MC named yoga restrictions and complete-yoga initial fixed-ghati exclusions',
 'vishanadi':'MC Vivaha scaled60-ghati nakshatra start and fixed four elapsed-ghati width',
 'yamaghanta_yoga':'MC Shubhashubha9 weekday/nakshatra pairs',
 'yamaghanta_kala':'MC commentary weekday ordinal of full daylight sixteenth',
 'nakshatra_gandanta':'MC fixed-ghati intervals on original nakshatra parents',
 'tithi_gandanta':'MC fixed-ghati intervals on original tithi parents',
 'lagna_gandanta':'MC fixed-ghati intervals on original Lagna-sign parents',
 'tithi_sunrise_count':'one sunrise in complete tithi occurrence; retain overlap uncertainty',
 'durmuhurta':'Vivaha52-54 weekday prohibitions on both full daylight/night fifteen-deity tables',
}

_EVENTS={
 'calendar':('calendar_phase','calendar_ingress','karana'),
 'star_history':('all_historical_padas','historical_nature_phase','Moon_clearance','Moon28_clearance','all_current_padas'),
 'pata':('yoga','nakshatra','Sun_discrete','Moon_discrete'),
 'solar_ingress':('Sun_sign_ingress','sunrise','shifted_ingress_edges'),
 'planetary_ingress':('all_sign_ingresses','shifted_ingress_edges'),
 'kartari':('all_current_padas','all_motion_stations','combustion','Moon_phase'),
 'jupiter_availability':('Jupiter_east_appearance','Jupiter_west_disappearance','availability_waiting_period'),
 'venus_availability':('Venus_east_appearance','Venus_east_disappearance','Venus_west_appearance','Venus_west_disappearance','availability_waiting_period'),
 'godhuli':('solar_half_set','solar_full_set','godhuli_edges','all_current_padas','sunrise'),
}
_SOLAR={'wedding_weekday','day_eighth','kulika','durmuhurta','yamaghanta_yoga','yamaghanta_kala','solar_bana','lagna_day_night'}
_PARENTS={'nitya_yoga','vishanadi','nakshatra_gandanta','tithi_gandanta','lagna_gandanta','tithi_sunrise_count'}
_DERIVED={'calendar','star_history','planetary_ingress','jupiter_availability','venus_availability','personal_tara','godhuli','broad_remedies'}
_COMPONENTS={
 'nitya_yoga':('mc_34_35_fixed_ghati_temporal_half.v1',),
 'vishanadi':('mc_vivaha_49_51.v1','mc_avasthi_scaled_start_fixed_width.v1'),
 'yamaghanta_yoga':('mc_shubhashubha_9_yamaghanta.v1',),
 'yamaghanta_kala':('mc_shubhashubha_37_sixteenths.v1',),
 'nakshatra_gandanta':('mc_vivaha_43_fixed_ghati.v1',),
 'tithi_gandanta':('mc_vivaha_43_fixed_ghati.v1',),
 'lagna_gandanta':('mc_vivaha_43_fixed_ghati.v1',),
 'personal_tara':('mc_gochara_13_quarters.v1','mc14_firstborn_Janma_composition'),
 'lagna_components':('mc_avasthi_vivaha_84_four.v1','mc_vivaha_84_optional_pisces.v1',
                     'bphs_3_11_verse_phase_same_sign.v1','mc_vivaha_88_natural_avasthas_orb.v1'),
}


def marriage_rule_contracts():
    result=[]
    for rule in RULES:
        family=rule.rule_id
        events=_EVENTS.get(family,('all_current_padas','karana','yoga','Moon_phase'))
        if family in _SOLAR:
            events+=('sunrise','sunset','full_parent_affine_edges')
        if family in _PARENTS:
            events+=('complete_phase_parents','full_parent_affine_edges','sunrise')
        if family=='lagna_components':
            events+=('combustion','all_motion_stations')
        fixtures=('tests/fixtures/marriage_election_sources.json',
                  'tests/unit/test_muhurta_marriage.py',
                  'tests/server/test_server_muhurta_marriage.py')
        if family.endswith('_availability'):
            fixtures+=('tests/unit/test_muhurta_marriage_visibility.py','tests/fixtures/marriage_visibility_cases.json')
        result.append(MarriageRuleContract(family,rule.finding_id,rule.locus,
            'primary source with explicitly named Moira composition' if family in _DERIVED else 'primary verse/commentary and identified canonical component',
            _FORMULAS[family],
            'UT1 elapsed events; sunrise weekday; separate27/unequal28-star and physical108-pada partitions',
            tuple(dict.fromkeys(events)),'unknown prerequisites remain unresolved; never authorize cancellation',
            fixtures,('evidence','astronomical_findings','personal_findings','composition_findings','search_receipt'),
            tuple(r.remedy_id for r in REMEDY_CONTRACTS if family in r.family_targets or
                  any(target.startswith(family+'.') for target in r.rule_targets)),_COMPONENTS.get(family,())))
    return tuple(result)


SUPPORTING_CONTRACTS=(
 ('M01','legacy guidance corrected/deprecated; preserve import and return shape; complete assessment is the replacement'),
 ('M29','same canonical direct evaluator through curated Python, facade, datetime and lossless REST/windows registries'),
 ('M30','source arithmetic and astronomical comparison are separate; no complete external marriage-oracle certification claimed'),
)
SOURCE_RECEIPT=('MC Avasthi2004',MC_URL,MC_SHA256)
HISTORY_COMPOSITION=(
 'MC58 names waning Moon among cruel bodies. Excluding election Moon as its own occupancy afflictor is a Moira composition, not an Avasthi exemption.',
 'Historical Moon remains a geometric piercing cause. Mercury association uses the named BPHS3.11 composition and event-time sky.',
)
