import sys
sys.path.append('d:/finalcode/skill-mind-ai/backend')
from app.services.coding_service import PROBLEMS_BANK

for p in PROBLEMS_BANK:
    if 'f' in p['starter_code'].split('\n') or ' f' in p['starter_code'] or 'f ' in p['starter_code']:
        print(f"Problem {p['id']} ({p['title']}) starter_code: {repr(p['starter_code'])}")
    if 'f' == p['test_wrapper'].strip():
        print(f"Problem {p['id']} ({p['title']}) test_wrapper: {repr(p['test_wrapper'])}")

print("Scan complete.")
