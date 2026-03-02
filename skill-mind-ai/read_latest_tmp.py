import os
import glob

temp_dir = os.environ.get('TEMP')
if not temp_dir:
    print("TEMP env var not found")
else:
    files = glob.glob(os.path.join(temp_dir, 'tmp*.py'))
    if not files:
        print("No tmp*.py files found in", temp_dir)
    else:
        latest_file = max(files, key=os.path.getmtime)
        print(f"Reading {latest_file}:")
        with open(latest_file, 'r') as f:
            lines = f.readlines()
            for i, line in enumerate(lines):
                print(f"{i+1}: {repr(line)}")
