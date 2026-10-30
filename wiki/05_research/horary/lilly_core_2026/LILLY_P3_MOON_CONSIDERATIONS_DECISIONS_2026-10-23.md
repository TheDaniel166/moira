# Lilly P3 Moon and considerations decisions

Date: 2026-10-23. Baseline: `caec99b70e054921b8e404b12ddc4616d3d9b510`.
Status: **decisions and test-only fixture packet; runtime admission pending**.

This tranche specifies finite Moon/VOC alternatives and contextual
considerations from Lilly's 1647 general doctrine. It does not change the
existing horary/perfection contracts, generic VOC helper, P2 evidence, public
exports, native code or REST. Historical statements in the preceding packets
remain their original admission checkpoints.

Read the [source collation](LILLY_P3_SOURCE_COLLATION_2026-10-23.md),
[fixture bundle](../../../../tests/fixtures/horary/lilly_p3_moon_considerations_2026_10_23.json),
[reference checks](../../../../tests/unit/test_lilly_p3_source_fixtures.py) and
[read-only validator](validate_p3_packet.py) together. The bundle is research
data and an independent expectation set for a future implementation. It is not
runtime configuration, a complete chart reconstruction or a predictive golden.

## Governing object and evidence layers

The proposed object is a source-qualified lunar evidence record at an explicit
question epoch. It keeps astronomical contact/motion evidence, source
propositions, operational policy choices, qualifications and unresolved inputs
separate. A caution has a trigger, scope, source attribution and qualification;
it is not a universal chart-validity or outcome switch.

Future astronomical inputs must retain UT1 query/event times and their
ephemeris-time adapter, tropical geocentric longitude/frame policy, event
uncertainty, body/aspect universe, and coverage. Synthetic fixtures instead use
seconds relative to an artificial question at zero. These offsets are neither
historical JDs nor ephemeris predictions. Source examples retain null epochs,
speeds and locations when the text omits them.

## Moon, application and VOC decisions

| ID | Decision and source | Implementation consequence |
|---|---|---|
| M01 | P.112 describes separation followed by no further application during the sign. Pp.107-108 distinguish platick application and exact contact. Preserve two named operational readings. | `exact_before_ingress_candidate` and `application_in_remaining_sign_candidate` must be selected explicitly; `voc_default` is null. A10's unique historical interpretation remains open. Neither is an alias for the existing generic `traditional` mode. |
| M02 | Pp.107-110 distinguish approaching, exact contact, initial separation and complete escape from rays. | Retain independent exact-contact and application-episode records. Reuse the P2 p.107 second-set strict moiety policy for the candidate episodes. The p.110 six-minute discussion is not a numerical root tolerance or an automatic delay of separation. |
| M03 | Pp.112,124 require lunar applications/separations to be considered. | Retain every supplied contact and episode, their evidence IDs, past-separation coverage, future coverage, and tied groups. Positive evidence can disprove void status under partial coverage; a no-connection claim needs complete coverage for that definition. |
| M04 | Pp.108-109 define the classical conjunction and four major aspects, including both directed orientations. | Moon's partners are Sun, Mercury, Venus, Mars, Jupiter and Saturn. Directed targets are 0,60,90,120,180,240,270,300 degrees. Modern planets, nodes, self contacts and minor aspects do not decide these candidates. |
| M05 | A sign endpoint and the onset of separation are distinct from a future contact. The source gives no numerical ordering tolerance. | Query-time contact and ingress-coincident/overlapping uncertainty are explicit boundary evidence. Preserve all ties; do not order by body iteration or silently inherit v1's one-second tie policy. |
| M06 | P.122 qualifies VOC testimony by very strong principals and by Taurus, Cancer, Sagittarius or Pisces. | Preserve raw VOC and each qualification independently. A named-sign qualification or supported qualitative strength may be present; incomplete strength context stays unknown. Neither qualification asserts success or cancels the raw VOC finding. |
| M07 | P.124 rejects the last-separated planet as an added querent significator. The following next-applied assignment is reported as their usage. | Keep sequence identities without automatic additional role assignment. Preserve rejected and reported propositions separately; next-applied co-quesited admission still needs practice/case evidence. |
| M08 | P.114 distinguishes the Moon's oriental and occidental halves of the solar cycle. | For directed elongation `(Moon-Sun) mod 360`, the open 0-180 half is occidental and 180-360 oriental. Conjunction/opposition remain boundaries. This geometric label supplies no observed visibility or universal strength verdict. |

### Exact-contact candidate

Query time is `q`; Moon's next sign exit has interval `[e_low,e_high]`.
A contact has `[c_low,c_high]`. A definite remaining contact satisfies
`q < c_low` and `c_high < e_low`. A definitely past contact has `c_high < q`;
a definitely later-sign contact has `c_low > e_high`. A contact at the query,
at ingress or overlapping either boundary is unresolved for this ordering.
An unambiguous in-sign witness makes raw VOC absent even if another contact is
uncertain. Otherwise a boundary witness or partial/unavailable exact scan
keeps it unknown. With complete exact coverage and no remaining connection,
raw VOC is present only when prior separation is established. Missing past
history remains unknown; an explicitly unmet separation precondition is
reported as not applicable to the p.112 separated-planet proposition before
testing that proposition's remaining conditions. This explicit applicability
result also survives partial coverage or an independently known connection.

This is an operational candidate, not a proof that p.112 means exactitude.
The existing generic VOC window starts at its last exact contact; its endpoint
ownership and behavior remain unchanged.

### Application candidate

An application episode is an already established **open** interval `(a,b)`:
the selected aspect residual is decreasing, its absolute value lies strictly
within the selected summed moiety, and the signs behold by that target aspect.
Its record must retain the positions, relative motion, orb policy, sign
relation and evidence provenance that establish those predicates. The test
packet supplies such episodes as synthetic premises; it does not calculate or
validate them from an ephemeris. A station, loss of approach, orb exit or sign
relation change ends the episode. Neither a future exact contact nor a linear
extrapolation alone proves the episode.

A definite intersection with the remaining sign exists when
`max(q,a) < min(e_low,b)`. If an intersection is possible only before `e_high`,
it is unresolved. An episode beginning exactly at sign exit or ending exactly
at the query is outside the remaining interval. Already-active episodes and
later orb entries both count when their interior meets the remaining sign.
Use application coverage independently from exact-contact coverage, then the
same prior-separation rules as above. Do not infer absence of application from
an empty exact-contact list.

A VOC qualification's applicability is unknown while raw VOC is unknown;
when raw VOC is absent, that particular qualification is not applicable.
The underlying sign/strength facts remain separately available in both cases.

The two candidate readings deliberately disagree when an eligible application
exists before ingress but exact completion does not. Interrupted intention is
a second distinction. These are synthetic counterexamples, not reconstructed
Lilly charts. The force of "forthwith" remains a historical ambiguity; no
arbitrary number of minutes is inserted as its definition.

## Contextual considerations

| ID | Source decision | Inputs, qualification and limit |
|---|---|---|
| C01 | P.122 early Ascendant: zero/first/second degrees. Operational interval `[0,3)`. | Exception requires both a qualitative very-young assessment and descriptive correspondence. Each needs supplied context/provenance. Do not invent a youth cutoff or treat one limb as sufficient. |
| C02 | P.122 late Ascendant: 27/28/29 degrees. Operational interval `[27,30)`. | Age correspondence OR an accurately timed event figure qualifies this caution. The latter needs event-figure purpose and a certain event time; a precisely timed question alone is insufficient. No age-matching formula is supplied. |
| C03 | P.122 late Moon: especially Gemini, Scorpio or Capricorn. | The passage supplies no finite degree cutoff. A longitude, including 27 or 29 degrees, cannot by itself establish the qualitative trigger. Keep a supplied qualitative assessment separately from the three-sign emphasis. |
| C04 | P.122 Via Combusta: last 15 Libra / first 15 Scorpio, attributed to "some". | Candidate interval `[195,225)` is a stated continuous-coordinate ownership convention. Preserve the attribution and boundary choice; do not merge it with the late-Moon caution or assert sole Lilly endorsement. |
| C05 | Pp.122-123 Saturn and seventh-house warnings have different wording. | Separate Saturn in first, Saturn in seventh, p.122 afflicted cusp/retrograde or impeded lord, and p.123 unfortunate/fallen/in-malefic-term lord. Apply the explicit non-seventh-topic qualification only to p.122's artist warning. Do not silently transfer that exception to every later warning. Affliction/impediment/fortunate testimony need source-qualified evidence; unspecified context is unknown. |
| C06 | Pp.113-114 combustion requires the same sign and the separate 8:30 limit. Beams: 17 degrees; cazimi: 17 arcminutes. | Retain geometry, same-sign status and each exact threshold boundary independently. The fixture reference reports boundary classes rather than a new inclusive/exclusive solar default. Cazimi is distinguished from the ordinary combustion caution. The p.113 10-degree contradiction remains quarantined. |
| C07 | Pp.121-122 hour agreement can be identity, triplicity or nature. | Retain the three routes and question/time/location binding. The five asserted Mars-hour examples supply no historical date or location for astronomical calculation. Missing hour evidence does not establish disagreement. P3 adds no chart-invalidity aggregator. |
| C08 | P.123 balanced fortunate/unfortunate testimony calls for deferral. | The passage does not enumerate a universal set of votes or numerical equality test. Keep source-qualified balance evidence, components and provenance; arbitrary counts or a dignity total cannot establish the rule. |

For C01/C02, preserve the raw degree trigger and exception separately. A known
failed raw trigger makes the caution absent even when contextual inputs are
missing. With a true trigger, a known exception qualifies that caution; a
known absent exception leaves it present; an unresolved exception keeps the
qualified result unknown. A resolved exception is not a positive prediction.
Unknown geometry, topic or supplied qualitative evidence must be distinguished
from a demonstrated negative proposition.

C01 also retains the source's emphasis on short-ascension signs as printed:
Capricorn, Aquarius, Pisces, Aries, Taurus and Gemini. This is a textual list,
not a latitude-independent astronomical classification or a restriction of
the early caution to those six signs. Qualitative strength input for M06 must
identify the actual principal roles, evaluation epoch and supporting evidence;
the synthetic collective flag is a fixture premise, not an admitted public API.

The p.123 seventh-lord clause is inventoried but its entire vocabulary is not
reduced to a fall-only predicate. P2 can supply a particular fall or dignity
witness. It cannot define "unfortunate" or "impeded" by summing points. Likewise,
the p.122 strength qualification is not satisfied automatically by one P2
dignity or a chosen score threshold.

## Fixture contract and next runtime gate

The bundle holds 22 page images by provenance reference, 16 decisions,
11 documentary claims and 193 fixtures in 13 families. Five fixtures reproduce
the asserted Mars-hour teaching examples; two preserve p.124 role propositions;
the remaining controls are explicitly synthetic. No original source images
are packaged. Both witnesses are photographs of the same edition, not
independent doctrinal authorities or observed-outcome records.

The test-only predicates check interval/uncertainty logic, both VOC candidates,
the full classical contact universe, qualifications, source literal sets,
solar and degree boundaries, role attribution and missing-context behavior.
They do not constitute a hidden production interpreter. Portable integrity
checks use explicit exceptions, including under Python `-O`/`-OO`, and may
verify every cached image's byte count and SHA-256. The original packet and
P2 fixtures remain unchanged.

Before runtime admission: implement typed evidence and episode derivation under
these named policies; bind every astronomical input/coverage receipt; verify
real lunar search and uncertainty boundaries against independent geometry;
test all supplied witnesses/ties without truncation; integrate contextual
inputs without changing v1; and record an actual implementation receipt.
Whole-system perfection precedence/continuation belongs to P4. Historical chart
reconstruction, symbolic timing, testimony ontology, latitude/speed/visibility
judgement and the complete fortitude table remain separately admitted work.

Run the portable packet check with the project's interpreter:

```powershell
.\.venv\Scripts\python.exe wiki/05_research/horary/lilly_core_2026/validate_p3_packet.py
.\.venv\Scripts\python.exe wiki/05_research/horary/lilly_core_2026/validate_p3_packet.py --cache C:/dev/outputs/lilly-p3-moon-considerations-20261023
.\.venv\Scripts\python.exe -m pytest tests/unit/test_lilly_p3_source_fixtures.py -q
```
