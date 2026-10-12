"""Compatibility module for the shared event-search clocks owner."""
import sys
from ._event_search import clocks as _owner

sys.modules[__name__] = _owner
