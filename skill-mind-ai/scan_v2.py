import sys
sys.path.append('d:/finalcode/skill-mind-ai/backend')
from app.services.coding_service import PROBLEMS_BANK

for p in PROBLEMS_BANK:
    sc = p['starter_code']
    if 'f' in sc.split() or any(line.strip() == 'f' for line in sc.split('\n')):
        print(f"Problem {p['id']} ({p['title']}) has stray 'f' in starter_code!")
        print(repr(sc))
    
    tw = p['test_wrapper']
    if tw.strip() == 'f':
        print(f"Problem {p['id']} ({p['title']}) has stray 'f' in test_wrapper!")

print("Scan finished.")
