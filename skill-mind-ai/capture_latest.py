import os
import glob
import shutil

temp_dir = os.environ.get('TEMP')
files = glob.glob(os.path.join(temp_dir, 'tmp*.py'))
if not files:
    print("No temp files found")
else:
    latest_file = max(files, key=os.path.getmtime)
    print(f"Captured: {latest_file}")
    shutil.copy(latest_file, 'd:/finalcode/skill-mind-ai/latest_test.py')
