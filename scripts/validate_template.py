#!/usr/bin/env python3
"""Sanity-check the template before importing it into Switch Console:
YAML parses, every agent in the room exists, every @mention in the
kickoff/instructions refers to a defined agent, and no obvious secrets."""
import re, sys, yaml

path = sys.argv[1] if len(sys.argv) > 1 else "campus-campaign-desk.template.yaml"
text = open(path).read()
doc = yaml.safe_load(text)
errors = []
assert doc.get("version") == 1, "version must be 1"
names = {a["name"] for a in doc["agents"]}
for n in doc["room"]["agents"]:
    if n not in names:
        errors.append(f"room agent {n} not defined")
for m in re.findall(r"@(\{team\}-[a-z-]+)", text):
    if m not in names:
        errors.append(f"@{m} is not a defined agent")
if re.search(r"(api[_-]?key|token|password)\s*[:=]\s*\S+", text, re.I):
    errors.append("possible secret in template")
if re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text):
    errors.append("email address in template")
print("\n".join(errors) or f"OK: {len(names)} agents, room {doc['room']['name']}")
sys.exit(1 if errors else 0)
