import json
# imports json python library
from project_manager_agent import ProjectManagerAgent
# imports the pydantic class from the python model file

schema = ProjectManagerAgent.model_json_schema()
# requests json schema generation from the model class imported

with open("ProjectManagerAgent.schema.json", "w", encoding="utf-8") as file:
# open/creates `ProjectManagerAgent.schema.json` as a `file` to `write` with utf-8 encoding
    json.dump(schema, file, indent=2)
# writes the requested schema from the imported pydantic class as json

print("Schema written.")
# prints in the terminal
