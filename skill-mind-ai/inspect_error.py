import json

with open('api_output.json', 'rb') as f:
    text = f.read().decode('utf-16')
    json_str = text.split('\n', 1)[1]
    # Replace single quotes with double quotes for valid JSON
    # This is risky but since it's just a test response it might work
    try:
        data = json.loads(json_str.replace("'", '"'))
        for res in data.get('test_results', []):
            print(f"Test {res['test']}: {res['error']}")
    except Exception as e:
        print(f"JSON Parse Error: {e}")
        print("Raw JSON-ish string:")
        print(json_str)
