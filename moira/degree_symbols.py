from typing import Optional
import math

from .sabian_symbols import SABIAN_SYMBOLS

__all__ = [
    "get_sabian_symbol",
    "get_degree_index",
]

def get_degree_index(longitude: float) -> int:
    """
    Returns the 1-indexed degree (1-30) for a given longitude within a sign (0.0 to 29.999...).
    Example: 
    0.0 -> 1
    0.5 -> 1
    1.0 -> 2
    15.3 -> 16
    29.9 -> 30
    """
    if not (0.0 <= longitude < 30.0):
        raise ValueError(f"Longitude within sign must be between 0.0 and 29.999..., got {longitude}")
    
    # math.floor(longitude) + 1 gives the 1-indexed degree
    return math.floor(longitude) + 1


def get_sabian_symbol(sign: str, sign_longitude: float) -> Optional[str]:
    """
    Returns the Sabian Symbol text for a given sign and longitude (0.0-29.999...).
    
    Parameters:
    - sign: Capitalized sign name, e.g. "Aries", "Taurus"
    - sign_longitude: The planet/point's position within the sign (0.0 to 30.0)
    
    Returns:
    - The textual symbol, or None if the sign is unrecognized.
    """
    degree = get_degree_index(sign_longitude)
    
    sign_dict = SABIAN_SYMBOLS.get(sign)
    if not sign_dict:
        return None
        
    return sign_dict.get(degree)
