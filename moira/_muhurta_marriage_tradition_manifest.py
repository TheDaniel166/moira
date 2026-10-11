"""Finite VV/KP rule registry, source choices and transition ownership."""
from dataclasses import dataclass

from . import _muhurta_marriage_tradition_sources as S
from ._muhurta_marriage_manifest import MarriageRuleContract,MarriageRemedyContract

_DISCRETE=('all_current_sign_pada_boundaries','Moon_phase','lagna_discrete')
_TIME=('sunrise','sunset','phase_parent_edges','derived_fixed_or_proportional_edges')
_CALENDAR=('physical_amanta_phase_and_ingress','Sun_discrete','tithi')
_HISTORY=('all_historical_padas','historical_Mercury_nature','Moon27_complete_passage','historical_uncertainty_bands')
_PLACEMENT=(*_DISCRETE,'all_motion_stations','angular_combustion_orbs')

# Every tuple is family, selected source locus, executable interpretation,
# transitions. The rule-to-transition test requires all emitted families here.
COMMON=(
 ('wedding_star','VV1.3; KP XIV116','eleven ordinary wedding stars including Mula',_DISCRETE),
 ('calendar','VV1.3-5/10.1-4; KP XIV121-122','physical Amanta; edition-specific lunar/solar precedence',_CALENDAR),
 ('intercalation','VV17.6; KP XXXIII','ordinary month required; unavailable physical month remains unknown',_CALENDAR),
 ('availability','VV5.8-9; KP XIV117/XXXIII219','Jupiter/Venus own geometry and side-specific elapsed-day waits',('profile_visibility_contacts','motion_qualified_orbs','derived_wait_edges')),
 ('solar_ingress','VV8.12/17.6; KP XXXIII212','VV16 ghati each side; KP30/60/180 each side by entered Sun sign',('Sun_sign_ingress','derived_ingress_edges')),
 ('karana','VV17.6; KP XXXIII220','VV Vishti; KP Vishti plus Kinstughna/Shakuni/Chatushpada/Naga',('karana',)),
 ('nitya_yoga','VV1.21; KP XXXIII205','VV fixed initial6/5/3/3/9/6 ghatis plus Parigha half and two whole; KP nine whole',('yoga','derived_yoga_edges')),
 ('tithi_sunrise_count','VV17.6; KP XXXIII','one sunrise in whole parent tithi; missing/overlap unresolved',('tithi','sunrise')),
 ('day_eighth','VV8.12; KP XXXIII212','VV proportional daylight yama-ardha table; KP fixed90-minute Yamaganda',_TIME),
 ('nakshatra_gandanta','VV8.12+MC43 adapter; KP II49','VV quantitative MC fixed-ghati composition; KP last/first2 fixed ghatis',_TIME),
 ('tithi_gandanta','VV8.12+MC43 adapter; KP II49','VV quantitative MC composition; KP last2 fixed ghatis of5/10/15 each paksha',_TIME),
 ('navamsa','VV4.8; KP XIV117','VV human signs with Sagittarius first half; KP fixed benefic-owned D9',_DISCRETE),
 ('placement','VV5/13/17; KP XIV117-119','edition-specific per-body house restrictions and retained testimony',(*_PLACEMENT,'VV_bhava_sandhis')),
 ('kartari','VV5.7; KP XXXIII208','VV both malefic flanks Lagna/Moon; KP both retrograde flanks Lagna',_PLACEMENT),
 ('moon_association','VV5.2; KP XIV124','VV same-sign malefic or Venus; KP any other same-sign planet',_DISCRETE),
 ('star_history','VV1.23/17.2; KP XIV123','nearest previous/current/next occupied star; VV two Moon clearances; KP no MC reset',_HISTORY),
)
VV_ROWS=(
 ('five_line','VV1.6-9/17.3','eight reciprocal28-star pairs; ordinary whole star, no necessity pada release',_DISCRETE),
 ('latta','VV1.11-13','eight forward inclusive27-star projections; Moon only Purnima',_DISCRETE),
 ('ekargala','VV1.14-19','nine named yogas plus odd inclusive28 count; detailed chapter over recap parity',(*_DISCRETE,'yoga')),
 ('solar_fourteenth','VV1.10/17.4','14th inclusive Moon27 from Sun27',_DISCRETE),
 ('pata','VV1.20','six named yoga endings; full owning Moon-star occurrence',('yoga_endings','nakshatra_parent')),
 ('navamsa_friendship','VV4.8/3.17-21','D9 lord in directed Yavana friends of D1 seventh lord or same lord',_DISCRETE),
 ('navamsa_lord_house','VV4.9/17.6','D1 placement of D9 Lagna/seventh lords cannot be2/3/8/12 from both corresponding D1/D9 references',_DISCRETE),
 ('navamsa_own_lord_support','VV6.3','D9 own lord occupies or fully aspects D9 sign from D1',_DISCRETE),
 ('navamsa_lord_debility','VV4.8','explicit sign-debility subset of qualitative weakness',_DISCRETE),
 ('movable_combination','VV4.17','movable Lagna and D9 with Moon Libra/Capricorn',_DISCRETE),
 ('seventh_occupancy','VV6.3/13.2/11','seventh from Lagna/Moon; narrowly qualified intrinsic Moon and selected benefic exceptions',_PLACEMENT),
 ('protected_full_jamitra','VV13.12-13','malefic at55th inclusive physical Navamsa from Moon; never cancel',_DISCRETE),
 ('jupiter_sign','VV5.5','Leo or Capricorn Jupiter',_DISCRETE),
 ('division_lord_sixth','VV13.1','Lagna D1/D3/D9 lord in D1 sixth',_DISCRETE),
 ('combustion','VV5.2/13.1','Moon/Navamsa-lord combustion under explicitly named avasthas angular-orb adapter',_PLACEMENT),
 ('hora','VV8.8-11','angular15-degree hora and fixed one-hour sunrise hora; own six-varga majority/weekday/night relief',(*_TIME,'Lagna_minus_Sun_15deg','D12_2.5deg','unequal_D30_edges')),
 ('latta_history','VV17.2','four malefic projected stars until two actual complete Moon traversals',_HISTORY),
 ('kulika_day','VV8.12','weekday ordinal14/12/10/8/6/4/2 of daylight fifteenths',_TIME),
 ('kulika_night','VV8.12','weekday ordinal13/11/9/7/5/3/1 of night fifteenths',_TIME),
 ('lagna_gandanta','VV8.12+MC43 quantitative adapter','explicit MC half-ghati end/start Lagna parents',_TIME),
 ('eclipse_seven_days','VV1.21','global eclipse occurrence through7 elapsed UT1 days after last contact',('global_shadow_contacts','derived_contact_plus7_days')),
 ('event_star_contamination','VV1.22-23','Moon/Lagna star touched by eclipse or five-planet longitude conjunction;2 subsequent traversals clear, proving older events irrelevant',(*_HISTORY,'ten_pair_longitude_conjunctions','global_shadow_contacts','Moon27','Lagna27')),
 ('krantisamya','VV1.23/17.3','actual equal signed apparent Sun/Moon declination in complete owning Moon-star occurrence',('apparent_declination_equality','nakshatra_parent')),
 ('personal_moon','VV6.1-6','both natal Moons; selected ordinary1/3/6/7/10/11 transit-house adapter',_DISCRETE),
 ('personal_transit','VV6.5/10.5-7/17.7','both participants Sun3/6/10/11 and Jupiter2/5/7/9/11; explicit symmetric ordinary adapter',_DISCRETE),
 ('personal_lagna','VV4.16/17.7','eighth/twelfth from natal Moon/Lagna; shared-lord exception for eighth only',_DISCRETE),
)
KP_ROWS=(
 ('calendar_grade','KP XIV116/121-122','best/middling lunar-month and ayana testimony; no new veto',_CALENDAR),
 ('tithi','KP XIV116/XXXIII219','best2/3/5/7/10/11/13; middling6/8/12/15, Krishna1; Krishna9 onward and Shukla1 prohibited',('tithi',)),
 ('weekday','KP XIV117','Monday/Wednesday/Thursday/Friday',('sunrise',)),
 ('lagna','KP XIV117','best Gemini/Virgo/Libra; four prohibited signs; remaining middling',_DISCRETE),
 ('prishtodaya','KP XIV123; BJ1.10','Aries/Taurus/Cancer/Sagittarius/Capricorn prohibited',_DISCRETE),
 ('planet_strength','KP XXXIII219','Jupiter/Venus debility, natural-enemy sign or retrograde',_PLACEMENT),
 ('jupiter_venus_opposition','KP XXXIII219','opposite whole signs',_DISCRETE),
 ('ekargala','KP XXXIII206-207','27-star head with13 reflected pairs; one of9yogas; day only',(*_DISCRETE,'yoga','sunset')),
 ('shadvarga','KP XXXIII216-219; BJ1.7/9 adapter','any malefic-owned D1/D2/D3/D9/self-counted D12/unequal D30',(*_DISCRETE,'D12_2.5deg','unequal_D30_edges')),
 ('star_end','KP XXXIII219','last2 fixed ghatis of owning star',_TIME),
 ('month_end','KP XXXIII219','last3 elapsed UT1 days of physical Amanta lunation',_CALENDAR),
 ('year_end','KP XXXIII219','last fortnight of Chaitra-start Amanta year',_CALENDAR),
 ('ruthu_end','KP XIV122/XXXIII219','paired lunar seasons; last3 elapsed days of second month (same quantified month-end)',_CALENDAR),
 ('paksha_end','KP XIV122-123/116','last tithi; explicit Purnima permission takes precedence; Ayana end already in own ingress wait',('tithi',)),
 ('rasi_gandanta','KP II49','water final D9 segment/fire initial D9 segment',_DISCRETE),
 ('nakshatra_thyajyam','KP XXXIII222','27 fixed start offsets with four fixed ghati width; preceding-parent carryover retained',_TIME),
 ('tithi_thyajyam','KP XXXIII223','15 fixed offsets; bright parent only; four fixed ghati width with preceding-parent carryover',_TIME),
 ('weekday_thyajyam','KP XXXIII223','fixed offsets30/42/41/31/2/22/20 from sunrise, width4',_TIME),
 ('rasi_thyajyam','KP XXXIII223','source sign-specific Navamsa1/5/9 and paired weekday groups',_DISCRETE),
 ('shadaseethimukha','KP XXXIII207','first60 fixed ghatis after Sun enters movable5/fixed7/dual9 Navamsa',('Sun_physical_Navamsa_entry','entry_plus1_day')),
 ('eclipse_ketu_star','KP XIV124','during global eclipse with Moon Ashwini/Magha/Mula',('global_shadow_contacts','Moon27')),
 ('personal_tara','KP XIV123-124','both people, Tara3/5/7 and10/19; Janma only first-born groom',_DISCRETE),
 ('personal_jupiter','KP XIV116','bride Jupiter2/5/7/9/11 from natal Moon',_DISCRETE),
 ('birth_period','KP XIV124','first-born groom birth lunar month and absolute tithi; Janma in own Tara row',_CALENDAR),
)


def contracts(profile):
    prefix='vv' if profile==S.VV else 'kp'
    rows=COMMON+(VV_ROWS if profile==S.VV else KP_ROWS)
    return tuple(MarriageRuleContract(prefix+'.'+key,'M01-M07/M13' if profile==S.VV else 'M08-M10',
        locus,'source prescription with explicitly named astronomical/interpretive adapters',formula,
        'apparent geocentric Lahiri; fixed ghati=1/60 UT1 day unless proportional parent expressly named',
        tuple(events),'unknown retained; required missing/uncertain evidence prevents complete coverage',
        ('tests/fixtures/marriage_additional_tradition_sources.json','tests/unit/test_muhurta_marriage_traditions.py'),
        ('evidence','astronomical_findings','personal_findings','composition_findings','search_receipt'),
        tuple(r.remedy_id for r in remedies(profile) if prefix+'.'+key in r.family_targets or any(
            target==prefix+'.'+key or target.startswith(prefix+'.'+key+'.') for target in r.rule_targets)),(profile,))
        for key,locus,formula,events in rows)


def remedies(profile):
    if profile==S.VV:
        return (
            MarriageRemedyContract('vv5_3_jupiter_aspects_tenth_mars','VV5.3',(),('vv.placement.mars',),'full Jupiter aspect; both D1 and bhava otherwise in3/6/10/11','intrinsic_rule'),
            MarriageRemedyContract('vv13_2_qualified_full_moon','VV13.2',(),('vv.placement.moon','vv.seventh_occupancy.lagna.moon'),
                'Purnima, own/friend/benefic D1 lord and full friend-benefic aspect; no other forbidden Moon house','intrinsic_rule'),
            MarriageRemedyContract(S.VV_REMEDIES[0],'VV13.11',('vv.seventh_occupancy',),(),
                'only malefic seventh from Moon; qualified benefic Kendra/trine in own/friend sign aspects Moon; protected_full_jamitra never targeted'))
    return (
        MarriageRemedyContract('kp_xiv_specific_purnima_permission','KP XIV116',(),('kp.paksha_end',),'Purnima explicitly middling','intrinsic_rule'),
        MarriageRemedyContract(S.KP_REMEDIES[0],'KP XIV124',('kp.tithi','kp.weekday','kp.prishtodaya'),(),
            'own/exalted direct noncombust Mercury/Venus/Jupiter in Lagna; explicit finite subset; no strength-number subtraction'))


@dataclass(frozen=True,slots=True)
class AdditionalMarriageProfile:
    """Inspectable finite ordinary profile; research traditions are not aliases."""
    profile: str
    personal_profile: str
    navamsa_profile: str
    source_receipt: tuple[str,str]
    source_fingerprint: str
    rule_contracts: tuple[MarriageRuleContract,...]
    remedy_contracts: tuple[MarriageRemedyContract,...]
    exclusions: tuple[tuple[str,str],...]


def profiles():
    return tuple(AdditionalMarriageProfile(profile,S.personal_profile(profile),S.VV_NAVAMSA if profile==S.VV else S.KP_NAVAMSA,
        S.source_receipt(profile),S.manifest_fingerprint(profile),contracts(profile),remedies(profile),S.EXCLUSIONS)
        for profile in (S.VV,S.KP))
