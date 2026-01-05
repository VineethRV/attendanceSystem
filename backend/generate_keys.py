"""
Generate unique registration keys for students
Creates a CSV file with USN and unique key pairs
"""

import csv
import secrets
import string
import os

def generate_unique_key(length=8):
    """Generate a random alphanumeric key"""
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_keys_csv(output_file='registration_keys.csv', start=1, end=450):
    """Generate CSV file with USN and unique keys"""
    
    keys_generated = []
    used_keys = set()
    
    for i in range(start, end + 1):
        usn = f"1RV23CS{i:03d}"
        
        # Generate unique key (ensure no duplicates)
        key = generate_unique_key()
        while key in used_keys:
            key = generate_unique_key()
        used_keys.add(key)
        
        keys_generated.append({
            'usn': usn,
            'registration_key': key,
            'used': 'NO'
        })
    
    # Write to CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['usn', 'registration_key', 'used'])
        writer.writeheader()
        writer.writerows(keys_generated)
    
    print(f"✅ Generated {len(keys_generated)} registration keys")
    print(f"📄 Saved to: {os.path.abspath(output_file)}")
    
    # Print first few entries as sample
    print("\nSample entries:")
    print("-" * 40)
    for entry in keys_generated[:5]:
        print(f"  {entry['usn']}: {entry['registration_key']}")
    print("  ...")
    for entry in keys_generated[-3:]:
        print(f"  {entry['usn']}: {entry['registration_key']}")
    
    return output_file

if __name__ == "__main__":
    generate_keys_csv()
