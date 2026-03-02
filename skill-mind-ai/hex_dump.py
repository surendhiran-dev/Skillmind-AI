with open('d:/finalcode/skill-mind-ai/backend/app/services/coding_service.py', 'rb') as f:
    lines = f.readlines()

for i in range(355, 375):
    if i < len(lines):
        print(f"{i+1}: {lines[i].hex()} | {repr(lines[i])}")
