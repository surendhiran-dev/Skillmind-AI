import os
import glob

temp_dir = os.environ.get('TEMP')
files = glob.glob(os.path.join(temp_dir, 'tmp*.py'))
latest_file = max(files, key=os.path.getmtime)
print(f"File: {latest_file}")
with open(latest_file, 'r') as f:
    for i in range(20):
        line = f.readline()
        if not line: break
        print(f"{i+1}: {repr(line)}")
