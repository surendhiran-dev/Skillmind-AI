
import json
import sys

def two_sum(nums, target):
    # Write your solution here
    pass


try:
    result = sorted(two_sum([2, 7, 11, 15], 9))
    print(json.dumps(result))
except Exception as e:
    print(json.dumps({"__error__": str(e)}))
