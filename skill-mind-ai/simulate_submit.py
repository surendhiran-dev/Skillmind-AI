import sys
import os
import json

# Add backend to path
sys.path.append('d:/finalcode/skill-mind-ai/backend')
from app.services.coding_service import run_test_cases, PROBLEMS_BANK

code = """def two_sum(nums, target):
    # Write your solution here
    pass"""

# Inject a print to see the script in coding_service.py's _run_single_test
# I'll just look at the first problem
problem_id = 4
results, score = run_test_cases(code, problem_id)
print(json.dumps(results, indent=2))
