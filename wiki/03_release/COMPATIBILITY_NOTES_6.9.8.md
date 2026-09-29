# Compatibility Notes - Moira 6.9.8

## Upgrade Boundary

Moira 6.9.8 follows 6.9.0. Most changes are additive, but the relationship
REST surface, the composite default, midpoint dials and Ashtottari Dasha change
results or contracts on purpose, because the former behaviour was wrong or
exposed internal bookkeeping.

## Removed Synastry Routes

These routes no longer exist and return HTTP 404:

- `POST /v1/synastry/contact-relations`
- `POST /v1/synastry/condition-profiles`
- `POST /v1/synastry/overlay-relations`
- `POST /v1/synastry/chart-condition`
- `POST /v1/synastry/network`

The synastry aspects, overlay and relationship-chart routes remain.

## Synastry Aspects

- Cross-chart aspects no longer set applying or separating from the two
  natal speeds, which describe unrelated moments.
- With nodes included, only the True Node takes part. Mean Node, Lilith and
  True Lilith are left out, so node contacts are no longer doubled.

## Composite Default Method

The composite route's default `method` is now `reference_place`. Callers that
relied on the former default must send `method: "midpoint"` explicitly.

## Unknown Birth Time

`time_unknown: true` on chart, houses and relationship requests:

- leaves the Moon out of the default body set, and rejects an explicit
  request for the Moon;
- rejects houses and any observer latitude or longitude.

The default is `false`, so existing requests are unchanged.

## Draconic Charts

`DraconicChart` and the REST draconic response gain `speed`,
`is_retrograde`, `origin`, `houses` and `angles`. All are optional additions.
A draconic chart requested with an observer is topocentric and says so in
`origin`; consumers comparing it with a geocentric natal chart should request
it without an observer.

## Midpoint Dials

90°, 45° and 22.5° dial coordinates now fold longitude by the dial modulus.
Every dial position, planetary picture, weighting, activation, tree and
cluster computed under 6.9.0 or earlier may differ; the new values are the
correct ones. Midpoint REST requests reject a nested `chart.include_nodes` in
favour of the top-level field.

## Ashtottari Dasha

The Ashtottari starting lord and balance follow BPHS 46.17-22. Births whose
Moon falls where the former rule and the BPHS allocation differ get a
different first lord and balance.

## Hellenistic Rays

Rays (aktinobolia) are now evaluated. In the chart-profile REST response,
`assemble_condition.ray` has `status: "evaluated"`, a `strikes` list and
`reason: null`; clients that read `reason` as always present, or expected
`"doctrine_not_admitted"`, must accept the evaluated form.

## New Additive Surfaces

al-Biruni mansions, Hellenistic rays, D60 deities, Sayanadi avasthas and
effects, the Chara Dasha `cycles` argument, antiscion motion state, the Sabian
Symbols lookup, lunar-orientation and Sothic REST routes, and small-body
returns are additive.

## Recommended Migration Sequence

```text
pip install --upgrade moira-astro==6.9.8
```

For services running `moira_server`:

```text
pip install --upgrade "moira-astro[server]==6.9.8"
```

Restart long-running engine and API processes after upgrading so the new
native extension and transport schemas are loaded together.
