import sys
sys.path.append('d:/finalcode/skill-mind-ai/backend')
from app.services.coding_service import PROBLEMS_BANK

for p in PROBLEMS_BANK:
    if p['id'] == 4:
        print(repr(p))
