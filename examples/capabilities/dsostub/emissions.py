import json
from gpiq.project import Project
from gpiq.validation.project_validation import validate_all


infile_name = "/tesp/lean_aug_8/sample.json"
with open(infile_name, 'r', encoding='utf-8') as infile:
  proj_json = json.load(infile)
val = validate_all(proj_json)
print(val)


proj = Project()
results = proj.calculate_project(proj_json)
outfile_name = "/tesp/lean_aug_8/results.json"
with open(outfile_name, 'w', encoding='utf-8') as outfile:
  json.dump(results, outfile, indent=2)
