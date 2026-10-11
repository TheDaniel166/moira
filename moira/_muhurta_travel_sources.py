"""Admitted travel components, separated from a complete travel tradition."""
from .muhurta_election import ElectionRuleContract as Rule, _manifest_digest

KP_SHA256='d082d5b3b29cb6c054f3cfe8e5ff50dfa6a66220128b52afa485c5a91c10c074'
KP_URL='https://www.astrojyoti.com/wp-content/uploads/2019/09/Kalaprakasika_text.pdf'
KP_WEEKDAY='kp_1917_weekday_direction_release.v1'
KP_MODULAR='kp_1917_travel_modular_tests.v1'
PROFILES=(KP_WEEKDAY,KP_MODULAR)
CARDINAL=('east','south','west','north')
DIRECTIONS=('east','southeast','south','southwest','west','northwest','north','northeast')
WEEKDAYS=(('east',(1,6)),('south',(4,)),('west',(0,5)),('north',(2,3)))
RELEASE_GHATIS=(('east',8),('south',22),('west',15),('north',12))
SHIFTS=(('illness',15),('fire',12),('authority',10),('theft',8),('disaster',4))
RULES=(
    Rule('travel.kp_weekday_direction','KP1917/1982 p148/PDF185',
         'specified weekday/direction restriction until strictly beyond8/22/15/12 fixed24-minute ghatis after local sunrise',
         ('departure',),('solar','direction'),('sunrise','release_offset'),'fixed_elapsed_ghati_composition'),
    Rule('travel.kp_three_moduli','KP1917/1982 p149,151/PDF186,188',
         'tithi*2 mod6, Sunday1 weekday*3 mod8, Ashwini1 star*4 mod6; all nonzero',
         ('departure',),('Sun','Moon','solar'),('tithi','Moon27','sunrise'),'explicit_tithi_ordinal_composition'),
    Rule('travel.kp_sun_moon_count','KP1917/1982 p151/PDF188',
         'inclusive Sun27 to Moon27 count mod7, preferred remainders1/4/5',
         ('departure',),('Sun','Moon'),('Sun27','Moon27')),
    Rule('travel.kp_shifted_panchakam','KP1917/1982 p151-152/PDF188-189',
         'one-based tithi+weekday+star+Lagna; independent shifts15/12/10/8/4 mod9; reject remainder5',
         ('departure',),('Sun','Moon','solar','Lagna'),('tithi','Moon27','sunrise','Lagna_sign'),
         'explicit_tithi_ordinal_composition'),
)
EXCLUSIONS=(
    ('complete_kp_travel','these separately named components do not implement the entire KP travel chapter'),
    ('disputed_kp_star_direction','KP p143/PDF180 duplicates westward star assignments; no guessed correction is admitted'),
    ('cross_source_cancellation','KP weekday release does not cancel MC restrictions or another KP component'),
    ('historical_outcome_prose','traditional category names describe source testimony, not predictions of injury, illness or disaster'),
    ('ritual_omens_and_safety','no ephemeris verifies rituals, omens, physical departure, or travel safety'),
)
MANIFEST_SHA256=_manifest_digest((PROFILES,KP_SHA256,WEEKDAYS,RELEASE_GHATIS,SHIFTS,RULES,EXCLUSIONS))
