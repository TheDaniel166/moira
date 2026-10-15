"""Exact-ratio transport with engine revalidation before serializing period trees."""
from dataclasses import fields, is_dataclass
from fractions import Fraction
from moira.kalachakra import KalachakraSequence, KalachakraCurrent, KalachakraInvariantError
from moira.kalachakra import _validate_sequence, _validate_current
from ..models.kalachakra import (
    KalachakraSequenceResponse, KalachakraCurrentResponse, KalachakraCatalogueResponse,
)


def _wire(value):
    if type(value) is Fraction:
        return {'numerator':str(value.numerator),'denominator':str(value.denominator)}
    if is_dataclass(value):
        return {f.name:_wire(getattr(value,f.name)) for f in fields(value)}
    if type(value) is tuple:
        return [_wire(v) for v in value]
    return value


def serialize_sequence(result):
    try:
        if type(result) is not KalachakraSequence:
            raise ValueError('typed sequence required')
        _validate_sequence(result)
        return KalachakraSequenceResponse.model_validate(_wire(result))
    except (ValueError,TypeError,AttributeError,KeyError) as exc:
        raise KalachakraInvariantError('invalid Kalachakra response invariant') from exc


def serialize_current(result):
    try:
        if type(result) is not KalachakraCurrent:
            raise ValueError('typed active line required')
        _validate_current(result)
        return KalachakraCurrentResponse.model_validate(_wire(result))
    except (ValueError,TypeError,AttributeError,KeyError) as exc:
        raise KalachakraInvariantError('invalid Kalachakra active response invariant') from exc


def serialize_catalogue(result):
    return KalachakraCatalogueResponse.model_validate(_wire(result))
