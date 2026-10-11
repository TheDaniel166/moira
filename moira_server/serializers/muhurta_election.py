"""Lossless projection including engine-computed findings and intervals."""
from dataclasses import asdict, fields, is_dataclass
from moira.muhurta_election import ElectionFinding
from moira._muhurta_election_dated import ElectionWindows


def election_values(value):
    if is_dataclass(value):
        result = {f.name: election_values(getattr(value, f.name)) for f in fields(value)}
        if isinstance(value, ElectionFinding):
            result.update(effective_restriction=value.effective_restriction, coverage_complete=value.coverage_complete)
        if isinstance(value, ElectionWindows):
            result.update(eligible_intervals=tuple(asdict(i) for i in value.eligible_intervals),
                          indeterminate_cell_indices=value.indeterminate_cell_indices)
        return result
    if isinstance(value, (tuple, list)):
        return tuple(election_values(v) for v in value)
    if isinstance(value, dict):
        return {k: election_values(v) for k, v in value.items()}
    return value
