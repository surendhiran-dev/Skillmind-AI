import json

with open('api_output.json', 'rb') as f:
    content = f.read().decode('utf-16')
    print(content)
