import os
import sys
# Add backend to path to import app
sys.path.append(os.getcwd())

from app.services.ai_service import MODULE_CONFIGS, HAS_AI

print(f"Overall HAS_AI: {HAS_AI}")
for mod, config in MODULE_CONFIGS.items():
    print(f"Module: {mod}")
    print(f"  has_ai: {config['has_ai']}")
    print(f"  has_or: {config['has_or']}")
    print(f"  client exists: {config['client'] is not None}")
    print(f"  model: {config['model']}")
