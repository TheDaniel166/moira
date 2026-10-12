"""Compatibility module for the shared event-search astronomy owner."""
import sys
from ._event_search import astronomy as _owner

sys.modules[__name__] = _owner
