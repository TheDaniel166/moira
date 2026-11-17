"""Transport-only errors for opt-in eclipse evidence products."""


class EclipseDiagnosticCoverageError(RuntimeError):
    """The selected ephemeris does not cover a requested diagnostic epoch."""
