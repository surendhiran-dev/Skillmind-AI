import json

code = "def two_sum(nums, target):\n    # Write your solution here\n    pass\n"
call_line = "result = sorted(two_sum([2, 7, 11, 15], 9))"

script = f"""
import json
import sys

{code}

try:
    {call_line}
    print(json.dumps(result))
except Exception as e:
    print(json.dumps({{"__error__": str(e)}}))
"""

with open('test_script.py', 'w', encoding='utf-8') as f:
    f.write(script)

with open('test_script.py', 'r') as f:
    lines = f.readlines()
    for i, line in enumerate(lines):
        print(f"{i+1}: {repr(line)}")
