import os
import json

def get_comment_heuristics(ext):
    if ext == '.py':
        return 'hash'
    elif ext in ('.cpp', '.cc', '.c', '.h', '.hpp'):
        return 'slash'
    return 'none'

def count_lines(filepath, comment_style):
    total = 0
    blank = 0
    comment = 0
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception:
        return 0, 0, 0
    
    in_block_comment = False
    
    for line in lines:
        total += 1
        stripped = line.strip()
        if not stripped:
            blank += 1
            continue
            
        if comment_style == 'hash':
            if stripped.startswith('#'):
                comment += 1
            elif '#' in stripped:
                # Basic check for trailing comment
                # In strict LOC, line counts as code even if trailing comment exists
                pass
        elif comment_style == 'slash':
            if in_block_comment:
                comment += 1
                if '*/' in stripped:
                    in_block_comment = False
                continue
                
            if stripped.startswith('//'):
                comment += 1
            elif stripped.startswith('/*'):
                comment += 1
                if '*/' not in stripped:
                    in_block_comment = True
            elif '/*' in stripped and '*/' not in stripped:
                # Started in middle of code line, counts as code
                pass
                
    return total, blank, comment

def main():
    target_dirs = {
        'moira': 'moira',
        'src': 'src',
        'tests': 'tests'
    }
    
    results = {}
    
    for label, folder in target_dirs.items():
        if not os.path.exists(folder):
            continue
            
        results[label] = {}
        
        for root, dirs, files in os.walk(folder):
            # Ignore __pycache__ and .venv if nested
            if '__pycache__' in root or '.venv' in root or '.git' in root:
                continue
                
            for file in files:
                filepath = os.path.join(root, file)
                ext = os.path.splitext(file)[1].lower()
                
                # Exclude binary files like .pyd, .pyc, .png, etc.
                if ext in ('.pyd', '.pyc', '.png', '.jpg', '.webp', '.dll', '.so', '.bsp', '.zip', '.tar', '.gz'):
                    continue
                    
                style = get_comment_heuristics(ext)
                tot, blk, cmt = count_lines(filepath, style)
                net = tot - blk - cmt
                
                # Classify subcategory
                if ext == '.py':
                    if label == 'tests':
                        subcat = 'Python Tests'
                    else:
                        subcat = 'Python Core'
                elif ext in ('.cpp', '.cc', '.c'):
                    subcat = 'C++ Core'
                elif ext in ('.h', '.hpp'):
                    subcat = 'C++ Headers'
                elif ext in ('.md', '.txt', '.rst'):
                    subcat = 'Documentation'
                elif ext in ('.toml', '.json', '.yml', '.yaml', '.xml', '.ini'):
                    subcat = 'Configuration/Data'
                else:
                    subcat = 'Other'
                    
                if subcat not in results[label]:
                    results[label][subcat] = {
                        'files': 0,
                        'total_lines': 0,
                        'blank_lines': 0,
                        'comment_lines': 0,
                        'net_code_lines': 0,
                        'extensions': set()
                    }
                    
                cat_dict = results[label][subcat]
                cat_dict['files'] += 1
                cat_dict['total_lines'] += tot
                cat_dict['blank_lines'] += blk
                cat_dict['comment_lines'] += cmt
                cat_dict['net_code_lines'] += net
                cat_dict['extensions'].add(ext)
                
    # Convert sets to lists for JSON serialization
    for label in results:
        for subcat in results[label]:
            results[label][subcat]['extensions'] = list(results[label][subcat]['extensions'])
            
    print(json.dumps(results, indent=2))

if __name__ == '__main__':
    main()
