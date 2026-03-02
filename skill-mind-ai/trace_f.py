with open('d:/finalcode/skill-mind-ai/backend/app/services/coding_service.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'script = f' in line:
        print(f"Found at line {i+1}")
        for j in range(i-5, i+25):
            if j < len(lines):
                print(f"{j+1}: {repr(lines[j])}")
        break
