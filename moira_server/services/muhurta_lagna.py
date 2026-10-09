"""Thin reader-preserving adapter; doctrine belongs to the engine."""
from ..serializers.muhurta_lagna import serialize_lagna_snapshot


def compute_lagna_snapshot(engine, request):
    return serialize_lagna_snapshot(engine.muhurta_lagna_for_datetime(
        **request.model_dump(exclude={'policy'}), policy=request.policy.to_engine()))
