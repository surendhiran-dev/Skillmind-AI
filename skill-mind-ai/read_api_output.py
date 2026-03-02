import json

with open('api_output.json', 'r') as f:
    text = f.read()
    # Skip the "Status: 200" line
    json_str = text.split('\n', 1)[1]
    data = json.loads(json_str.replace("'", '"')) # Simple fix for single quotes
    print(json.dumps(data, indent=2))
