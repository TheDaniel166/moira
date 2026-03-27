from pathlib import Path

# The source file
in_file = r"C:\Users\nilad\Downloads\modern-iau-star-names.csv"
# The clean destination
out_file = r"C:\Users\nilad\OneDrive\Desktop\Moira\moira\data\modern-iau-star-names-clean.csv"

def cleanse_encoding():
    try:
        raw_data = Path(in_file).read_bytes()
        
        # Try a few common difficult encodings first
        try:
            text = raw_data.decode('utf-8')
            encoding = 'utf-8'
        except UnicodeDecodeError:
            try:
                text = raw_data.decode('windows-1252')
                encoding = 'windows-1252'
            except UnicodeDecodeError:
                text = raw_data.decode('iso-8859-1', errors='replace')
                encoding = 'iso-8859-1 (with replacement)'
                
        print(f"Decoded successfully using: {encoding}")
        
        Path(out_file).parent.mkdir(parents=True, exist_ok=True)
        Path(out_file).write_text(text, encoding='utf-8')
        print(f"Successfully wrote cleansed file to {out_file}")
        
        lines = text.splitlines()
        for i, line in enumerate(lines[:5]):
            print(f"Line {i}: {line}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    cleanse_encoding()
