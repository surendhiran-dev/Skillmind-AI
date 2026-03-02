import sys
import os

# Mock the folder structure to import coding_service
sys.path.append('d:/finalcode/skill-mind-ai/backend')
from app.services.coding_service import PROBLEMS_BANK

for p in PROBLEMS_BANK:
    print(f"ID {p['id']}: {repr(p['starter_code'])}")
