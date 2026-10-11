"""Edition-separated ordinary marriage admission; never aliases of MC04.

All ordinals below are independently transcribed from the named scans. The
standard distinguishes the source's conclusions, quoted alternatives and
Moira's explicit astronomical adapters. Versioned profiles are finite scopes.
"""
from hashlib import sha256
from json import dumps

VV = 'vv_vasantalakshmi_1935_marriage_ordinary.v1'
KP = 'kp_1917_marriage_ordinary.v1'
VV_PERSONAL = 'vv_vasantalakshmi_1935_marriage_personal.v1'
KP_PERSONAL = 'kp_1917_marriage_personal.v1'
VV_NAVAMSA = 'vv_4_8_human_signs_sagittarius_first_half.v1'
KP_NAVAMSA = 'kp_xiv_benefic_owned_navamsa.v1'
VV_SHA = '793cc3c454a0c383bb3784886cd19e702d310b67aa39a597748b148da02cdfc0'
KP_SHA = 'd082d5b3b29cb6c054f3cfe8e5ff50dfa6a66220128b52afa485c5a91c10c074'
VV_URL = 'https://archive.org/details/in.ernet.dli.2015.329463'
KP_URL = 'https://www.astrojyoti.com/wp-content/uploads/2019/09/Kalaprakasika_text.pdf'
STARS = (3,4,9,11,12,14,16,18,20,25,26)
# VV1.6 diagram, PDF17, confirmed independently by17.3/PDF127.
# Hasta/UBhadra and Revati/UPhalguni: account for the Abhijit insertion.
# The pairs agree with MC04; VV ordinary whole-star qualification differs.
VV_FIVE_PAIRS = ((14,24),(22,9),(1,16),(21,3),(6,18),(26,12),(20,4),(27,11))
VV_LATTA = (('Sun',12),('Saturn',8),('Mars',3),('Rahu',20),
            ('Moon',7),('Mercury',22),('Jupiter',6),('Venus',24))
VV_FRIENDS = (('Sun',('Jupiter',)),('Moon',('Mercury','Jupiter')),
    ('Mars',('Mercury','Venus')),('Mercury',('Moon','Mars','Jupiter','Venus','Saturn')),
    ('Jupiter',('Sun','Moon','Mercury','Venus','Saturn')),
    ('Venus',('Mars','Mercury','Jupiter','Saturn')),('Saturn',('Mercury','Jupiter','Venus')))
VV_BUFFERS = (('Jupiter','east',10,14),('Jupiter','west',10,14),
              ('Venus','east',3,10),('Venus','west',10,5))
KP_BUFFERS = (('Jupiter','east',8,15),('Jupiter','west',8,15),
              ('Venus','east',7,10),('Venus','west',7,10))
KP_BEST_TITHIS = (2,3,5,7,10,11,13)
KP_MIDDLE_TITHIS = (6,8,12,15)  # Krishna1 is an additional explicit permission.
KP_BAD_MONTHS = (3,5,8,10)
KP_MIDDLE_MONTHS = (0,4,6)
PRISHTODAYA = (0,1,3,8,9)
EKARGALA_YOGAS = (0,5,8,9,12,14,16,18,26)
PATA_YOGAS = (8,9,13,16,21,26)
VV_REMEDIES = ('vv13_11_qualified_benefic_moon_aspect',)
KP_REMEDIES = ('kp_xiv_dignified_benefic_lagna_finite',)
# KP XIV/PDF117-119: retain these as testimony, independently of other rules.
KP_BAD_HOUSES = (
 ('Sun',(1,2,4,5,7,10,12)),('Moon',(1,4,6,7,8,12)),
 ('Mars',(1,2,4,5,7,9,10,12)),('Mercury',(7,8)),
 ('Jupiter',(7,8)),('Venus',(7,8)),('Saturn',(1,2,4,5,7,9,10,12)),
 ('Rahu',(1,2,4,5,6,7,8,9,10,12)),('Ketu',(1,2,4,7,8,12)))
KP_GOOD_HOUSES = (
 ('Sun',(3,6,8,9,11)),('Moon',(2,3,5,9,10,11)),
 ('Mars',(3,6,8,11)),('Mercury',(1,2,3,4,5,6,9,10,11,12)),
 ('Jupiter',(1,2,3,4,5,6,9,10,11,12)),('Venus',(1,2,3,4,5,6,9,10,11,12)),
 ('Saturn',(3,6,8,11)),('Rahu',(3,11)),('Ketu',(3,6,9,10,11)))


def buffers(profile,planet,side):
    """Specific chapter waiting periods override that edition's general rule."""
    rows=VV_BUFFERS if profile==VV else KP_BUFFERS
    return next((post,pre) for p,s,post,pre in rows if (p,s)==(planet,side))


def personal_profile(profile):
    return VV_PERSONAL if profile==VV else KP_PERSONAL


def source_receipt(profile):
    return (VV_URL,VV_SHA) if profile==VV else (KP_URL,KP_SHA)


def manifest_fingerprint(profile):
    from dataclasses import asdict
    from ._muhurta_marriage_tradition_manifest import contracts,remedies
    payload=(profile,source_receipt(profile),STARS,
        (VV_FIVE_PAIRS,VV_LATTA,VV_FRIENDS,VV_BUFFERS,VV_REMEDIES) if profile==VV else
        (KP_BUFFERS,KP_BAD_HOUSES,KP_GOOD_HOUSES,KP_BAD_MONTHS,KP_MIDDLE_MONTHS,KP_BEST_TITHIS,KP_MIDDLE_TITHIS,KP_REMEDIES),
        tuple(asdict(x) for x in contracts(profile)),tuple(asdict(x) for x in remedies(profile)),EXCLUSIONS)
    return sha256(dumps(payload,separators=(',',':')).encode()).hexdigest()


EXCLUSIONS=(
    ('compatibility_matching','VV chapter3 and KP natal matching belong to compatibility, not this elected anchor'),
    ('historical_social_prescriptions','Age, class, kinship and gendered character predictions are outside numerical timing'),
    ('family_ritual_spacing','Family ceremonies, death observances and ritual performance are separate contextual products'),
    ('whole_ceremony_duration','Elects the explicitly declared anchor only'),
    ('physical_visibility','VV uses the SS mathematical horizon adapter; KP uses its angular orbs; neither claims observed visibility'),
    ('godhuli','These are ordinary profiles; MC Godhuli permission is not imported'),
    ('full_natal_planetary_conditions','VV4/17 natal occupied-house/varga conditions require a separate full natal-chart profile; the admitted personal scope is Moon/Lagna and declared birth context'),
    ('horary_and_character_yogas','VV horary/prognostic chapters and KP outcome narratives are not extra timing vetoes'),
    ('unobserved_omens','Weather, earthquakes, meteors and other observed portents are not inferred from an ephemeris'),
)
