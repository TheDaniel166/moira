# Security Policy

## Supported Versions

Moira is a stable public engine. Security fixes are applied to the latest released version.

At this time, only the most recent release series is considered supported for security updates.

| Version | Supported |
|---------|-----------|
| Latest 1.x release | Yes |
| Older releases | No |

## Reporting a Vulnerability

If you discover a security vulnerability in Moira, please report it privately.

Do **not** open a public GitHub issue for suspected security vulnerabilities.

Instead, please report suspected security vulnerabilities privately by email to:

**isopgem@outlook.com**

When reporting an issue, please include as much of the following as possible:

- a clear description of the vulnerability
- affected version(s)
- conditions required to trigger it
- step-by-step reproduction details
- proof of concept, if appropriate and safe
- potential impact
- any suggested remediation, if known

Reports that are clear, reproducible, and responsibly scoped are the most helpful.

## What to Expect

Reasonable efforts will be made to:

- acknowledge receipt of a valid report
- investigate the issue
- determine severity and scope
- prepare a fix if the report is confirmed
- coordinate disclosure in a responsible way

Response time may vary depending on report quality, complexity, and maintainer availability.

## Scope

Moira is a computational engine, not a hosted service.

That matters for security scope.

Security issues may include things such as:

- code execution vulnerabilities
- unsafe deserialization or parsing behavior
- malicious file handling risks
- dependency-related vulnerabilities with real impact
- denial-of-service vectors caused by malformed or adversarial inputs
- packaging or distribution compromises
- other issues that meaningfully affect the security of users or systems running Moira

## What Is Not a Security Vulnerability

The following are generally **not** considered security issues by themselves:

- numerical disagreements
- doctrinal disagreements
- validation disputes
- differences from other libraries or engines
- scientific or astrological interpretation disputes
- incorrect results without a security impact
- API design disagreements
- performance complaints without an exploit dimension
- feature requests framed as vulnerabilities

Those issues may still be important, but they should be reported through the normal issue tracker if appropriate.

## Responsible Disclosure

Please do not publicly disclose a vulnerability until it has been investigated and, where appropriate, fixed or mitigated.

Responsible disclosure helps protect users and gives the project a fair opportunity to assess and address legitimate issues properly.

## Dependency and Supply Chain Notes

Moira depends on third-party packages and external astronomical data sources as part of its broader operating environment.

If a vulnerability is reported in a third-party dependency, the issue will be evaluated in terms of actual impact on Moira’s usage and distribution model.

Not every upstream CVE automatically constitutes a material vulnerability in Moira, but relevant dependency risks will be taken seriously.

## No Security Warranty

While reasonable care is taken in the design and maintenance of Moira, no software can be guaranteed free of defects or vulnerabilities.

Users are responsible for evaluating Moira within their own environments, threat models, and deployment contexts.

## Final Note

Moira is maintained with a strong emphasis on correctness, transparency, and trustworthiness. Responsible security reporting is part of that trust.

If you believe you have found a legitimate vulnerability, report it privately and with as much precision as possible.
