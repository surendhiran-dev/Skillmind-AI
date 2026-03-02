with open('d:/finalcode/skill-mind-ai/frontend/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(340, 360):
    if i < len(lines):
        print(f"{i+1}: {repr(lines[i])}")
