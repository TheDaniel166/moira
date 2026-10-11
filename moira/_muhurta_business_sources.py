"""MC04 commerce: actor-specific source selections and explicit compositions."""
from .muhurta_election import ElectionRuleContract as Rule, _manifest_digest

PROFILE = 'mc_avasthi_2004_commerce.v1'
SOURCE_URL = 'https://archive.org/details/muhurta-chintamani-hindi'
SOURCE_SHA256 = '9e931eb7fdc1958516424590a168680be60753f4cfccea8f327cae973dfe4777'
PURPOSES = ('purchase', 'sale', 'first_opening_for_trade')
STARS = (('purchase',(26,23,0,14,21,13)), ('sale',(10,19,24,15,2,8,1)),
         ('first_opening_for_trade',(13,16,4,26,3,11,20,25,0,7,12)))
ROLE = dict(purchase='buyer', sale='seller', first_opening_for_trade='trading_operator')
# Sunday0 weekdays; one-based paksha tithis. MC04 1.5,6,8.
DEAD_CLASSES = (1,2,1,3,4,2,5)
KRAKACHA = (12,11,10,9,8,7,6)
DAGDHA = (12,11,5,3,6,8,9)
VISHA = (4,6,7,2,8,9,7)
HUTASHANA = (12,6,7,8,9,10,11)
TITHI_STARS = ((12,(8,)),(1,(20,)),(2,(16,)),(5,(9,)),(3,(11,20,25)),
               (11,(3,)),(13,(14,13)),(7,(12,18)),(9,(2,)),(8,(24,)),(6,(3,)))
RULES = (
    Rule('business.selected_star','MC04 2.16-17, printed33-34/PDF42-43',
         'actor-specific positive star selection; complement means absence of selected auspicious support',
         PURPOSES,('Moon','actor_role'),('Moon27',)),
    Rule('business.sale_tithi','MC04 2.17 sat-tithi; selected1.4-6,8,11-13,20/PDF11-19',
         'best paksha tier plus enumerated weekday/star/triple exclusions; no regional shunya import',
         ('sale',),('Sun','Moon','solar'),('tithi','Moon27','sunrise'),'named_best_tithi_composition'),
    Rule('business.sale_lagna','MC04 2.17/PDF42',
         'no Aquarius; seven-classical benefics1/2/4/5/7/9/10; malefics3/6/11',
         ('sale',),('seven_planets','Lagna'),('planet_signs','Lagna_sign','Moon_phase'),'named_seven_graha_reading'),
    Rule('business.vipani_panchanga','MC04 2.17/PDF42-43',
         'no Rikta, Tuesday or Aquarius Lagna',('first_opening_for_trade',),
         ('Sun','Moon','solar','Lagna'),('tithi','sunrise','Lagna_sign')),
    Rule('business.vipani_placements','MC04 2.17/PDF42-43',
         'Moon AND Venus in Lagna; no malefic8/12; other benefics2/10/11; specific precedes general',
         ('first_opening_for_trade',),('seven_planets','Lagna'),('planet_signs','Lagna_sign','Moon_phase'),
         'named_seven_graha_specific_over_general_reading'),
)
EXCLUSIONS = (
    ('other_financial_actions','lending, borrowing, incorporation, contracts and commodity-specific actions need their own source manifests'),
    ('personal_timing','this selected commerce manifest has no natal qualification; actor identity is contextual, not a supplied birth-chart score'),
    ('unselected_general_rules','sat-tithi uses the declared finite composition; regional shunya, unrelated ritual rules and other general yogas are not silently imported'),
    ('financial_prediction','source timing is not a prediction of profit or financial safety'),
    ('node_placement_extension','the disclosed placement quantifier uses seven classical grahas, not both opposite nodes'),
)
MANIFEST_SHA256 = _manifest_digest((PROFILE,SOURCE_SHA256,STARS,DEAD_CLASSES,KRAKACHA,DAGDHA,VISHA,HUTASHANA,TITHI_STARS,RULES,EXCLUSIONS))
