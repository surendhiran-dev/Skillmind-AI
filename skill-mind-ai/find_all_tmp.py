import tempfile
import os
import glob

tmpdir = tempfile.gettempdir()
print(f"Temp Dir: {tmpdir}")

files = glob.glob(os.path.join(tmpdir, 'tmp*.py'))
for f in files:
    print(f"File: {f}")
    with open(f, 'r') as file:
        content = file.read()
        if 'import json' in content:
            print("--- Content ---")
            print(content)
            print("---------------")
