import os, glob

for filepath in glob.glob('moira/**/*.py', recursive=True):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'from __future__ import annotations' in content:
        continue
    
    lines = content.split('\n')
    out_lines = []
    in_docstring = False
    docstring_char = None
    inserted = False
    
    for line in lines:
        if inserted:
            out_lines.append(line)
            continue
            
        stripped = line.strip()
        
        if not in_docstring and (stripped.startswith('"""') or stripped.startswith("'''")):
            out_lines.append(line)
            in_docstring = True
            docstring_char = stripped[:3]
            # Handle single-line docstring
            if len(stripped) >= 6 and stripped.endswith(docstring_char):
                in_docstring = False
                out_lines.append("\nfrom __future__ import annotations")
                inserted = True
        elif in_docstring:
            out_lines.append(line)
            if stripped.endswith(docstring_char):
                in_docstring = False
                out_lines.append("\nfrom __future__ import annotations")
                inserted = True
        else:
            # We are not in a docstring
            if stripped == '' or stripped.startswith('#'):
                out_lines.append(line)
            else:
                # Actual code starts here
                out_lines.append("from __future__ import annotations\n")
                out_lines.append(line)
                inserted = True
                
    # If file was completely empty or only comments
    if not inserted:
        out_lines.insert(0, "from __future__ import annotations\n")
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out_lines))

print("Fixed missing annotations.")
