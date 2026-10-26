"""Named Kalachakra occurrence doctrine, separate from exact interval materialization.

Santhanam rotates one natal row. Rao 2000 rule 4 advances through the eight
source rows of one Savya/Apasavya family. Row namespaces preserve that ownership
even in standalone period vessels. No caller-editable recipes are admitted.
"""
from dataclasses import dataclass
from types import MappingProxyType

from .kalachakra_policy import (
    PROFILE_ID, VERSION, RAO_PROFILE_ID, RAO_VERSION, ROWS, WEIGHTS,
    RULE_IDS, CONFLICT_IDS, RAO_RULE_IDS, RAO_CONFLICT_IDS,
)


@dataclass(frozen=True, slots=True)
class _Recipe:
    """Immutable admitted recipe identity and source decisions."""
    profile_id: str
    version: str
    namespace: str
    continuation: str
    deha_jeeva_reference: str
    source_ids: tuple[str,...]
    rule_ids: tuple[str,...]
    conflict_ids: tuple[str,...]


RECIPES = MappingProxyType({
    PROFILE_ID: _Recipe(PROFILE_ID,VERSION,"","natal_row_cycle","natal_row",
        ("L01","L02","L09","L11"),RULE_IDS,CONFLICT_IDS),
    RAO_PROFILE_ID: _Recipe(RAO_PROFILE_ID,RAO_VERSION,"R2000/","continuous_family_rows",
        "birth_nine_md_window",("L01","L02","L09"),RAO_RULE_IDS,RAO_CONFLICT_IDS),
})
ROW_OWNERS = MappingProxyType({recipe.namespace+row: recipe
    for recipe in RECIPES.values() for row in ROWS})


def recipe_for_row(row_id):
    """Resolve an exact source row identity without accepting arbitrary namespaces."""
    if type(row_id) is not str or row_id not in ROW_OWNERS:
        raise ValueError("unsupported Kalachakra row identity")
    return ROW_OWNERS[row_id]


def source_row(row_id):
    recipe = recipe_for_row(row_id)
    return ROWS[row_id[len(recipe.namespace):]]


def advance(row_id, position, steps):
    """Advance an occurrence under its row owner's explicitly admitted rule."""
    recipe = recipe_for_row(row_id)
    if recipe.continuation == "natal_row_cycle":
        cycle, pos = divmod(position+steps,9)
        return row_id,pos,cycle
    source_id = row_id[len(recipe.namespace):]
    group,pada = source_id.split('/')
    row_number = (int(group[1])-1)*4+int(pada)-1
    cycle, within = divmod(row_number*9+position+steps,72)
    row_number,pos = divmod(within,9)
    subgroup,pada = divmod(row_number,4)
    return f"{recipe.namespace}{group[0]}{subgroup+1}/{pada+1}",pos,cycle


def window(row_id, position):
    """Nine full occurrences, including source row identity and traversal cycle."""
    occurrences = []
    for i in range(9):
        row,pos,cycle = advance(row_id,position,i)
        occurrences.append((row,pos,cycle,source_row(row)[pos]))
    return tuple(occurrences)


def window_total(row_id, position):
    return sum(WEIGHTS[sign] for _,_,_,sign in window(row_id,position))


def birth_window(row_id, position):
    """Full nine-MD weight and the source-defined Deha/Jeeva reference."""
    recipe = recipe_for_row(row_id)
    signs = tuple(s for _,_,_,s in window(row_id,position))
    reference = source_row(row_id) if recipe.deha_jeeva_reference == "natal_row" else signs
    group = row_id[len(recipe.namespace):][0]
    deha,jeeva = (reference[0],reference[-1]) if group == 'S' else (reference[-1],reference[0])
    return sum(WEIGHTS[s] for s in signs),deha,jeeva,recipe.deha_jeeva_reference


def transition_reading(row_id, source_position, pair, seam):
    """Classify only the source owner's directed edges, with explicit conflict status."""
    recipe = recipe_for_row(row_id)
    if recipe.profile_id == PROFILE_ID:
        if seam:
            return "row_seam_not_classified",None,(),"KC_GATI"
        if pair in ((3,4),(4,3)):
            return "unresolved_source_conflict",None,("KC-10",),"KC_GATI"
        labels = {(5,3):"mandooki",(4,2):"mandooki",(11,7):"simhavlokan",(8,0):"simhavlokan"}
        rule_id = "KC_GATI"
    else:
        family = row_id[len(recipe.namespace):][0]
        labels = ({(5,3):"mandooki",(4,2):"mandooki",(11,7):"simhavlokan",(8,0):"simhavlokan"}
            if family == 'S' else
            {(3,5):"mandooki",(2,4):"mandooki",(7,11):"simhavlokan",(0,8):"simhavlokan"})
        # Rao 24.3.3(2): Vi-Cn-Le-Ge / Ge-Le-Cn-Vi are temporary
        # reversals. The central pairs also occur in ordinary progression.
        # Read the source neighbours even outside a returned/clipped window.
        reversal = (5,3,4,2) if family == 'S' else (2,4,3,5)
        if pair == reversal[1:3]:
            before_row,before_pos,_ = advance(row_id,source_position,-1)
            after_row,after_pos,_ = advance(row_id,source_position,2)
            context = (source_row(before_row)[before_pos],*pair,source_row(after_row)[after_pos])
            if context == reversal:
                labels[pair] = "markati"
        rule_id = "R2000_GATI"
    label = labels.get(pair)
    return ("classified" if label else "not_classified_by_profile"),label,(),rule_id


# Finite source-derived response domain, not a caller-editable denominator.
DENOMINATORS = tuple(sorted({1} | {window_total(row,pos) for row in ROW_OWNERS for pos in range(9)}))
