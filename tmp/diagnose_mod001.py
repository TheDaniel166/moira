import ast, sys
sys.path.insert(0, 'tests/unit')
from test_docstring_governance import MOIRA_ROOT

targets = [
    'bridges/harmograms.py', 'data/__init__.py', 'harmograms/compute.py',
    'harmograms/helpers.py', 'harmograms/models.py', 'harmograms/research.py',
    'lord_of_the_orb.py', 'lord_of_the_turn.py', 'lots.py',
    'nine_parts.py', 'parans.py', 'synastry.py', 'timelords.py'
]
for t in targets:
    path = MOIRA_ROOT / t
    raw = path.read_bytes()[:6]
    has_bom = raw[:3] == b'\xef\xbb\xbf'
    text = path.read_text(encoding='utf-8-sig')
    first30 = repr(text[:30])
    try:
        tree = ast.parse(text)
        ds = ast.get_docstring(tree)
        has_ds = bool(ds and ds.strip())
    except SyntaxError as e:
        has_ds = f'SyntaxError: {e}'
    print(f'{t}: has_docstring={has_ds}, bom={has_bom}, first30={first30}')
