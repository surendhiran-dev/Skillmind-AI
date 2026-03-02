from app import create_app, db
from sqlalchemy import inspect
import json

app = create_app()
with app.app_context():
    inspector = inspect(db.engine)
    schema = {}
    for table in inspector.get_table_names():
        schema[table] = [c['name'] for c in inspector.get_columns(table)]
    print(json.dumps(schema, indent=2))
