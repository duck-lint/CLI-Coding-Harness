import json
# imports json python library
from project_spec import ProjectSpec
# imports the pydantic class from the python model file

schema = ProjectSpec.model_json_schema()
# requests json schema generation from the model class imported

with open("ProjectSpec.schema.json", "w", encoding="utf-8") as file:
# open/creates `ProjectSpec.schema.json` as a `file` to `write` with utf-8 encoding
    json.dump(schema, file, indent=2)
# writes the requested schema from the imported pydantic class as json

print("Schema written.")
# prints in the terminal
