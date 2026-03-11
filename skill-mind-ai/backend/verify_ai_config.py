import os
import sys

# Add the backend directory to sys.path
sys.path.append(os.path.join(os.getcwd(), '..'))

from app import create_app
from app.services.ai_service import MODULE_CONFIGS, HAS_AI

app = create_app()
with app.app_context():
    print(f"Overall AI Enabled: {HAS_AI}")
    for mod in sorted(MODULE_CONFIGS.keys()):
        config = MODULE_CONFIGS[mod]
        print(f"Module: {mod}")
        print(f"  - Has AI: {config.get('has_ai')}")
        print(f"  - Has OR: {config.get('has_or')}")
        print(f"  - Client Opt: {'Present' if config.get('client') else 'None'}")
