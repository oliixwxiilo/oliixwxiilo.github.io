#!/usr/bin/env python3
"""Classify package dependencies as provided in-repo or external to this repository."""
import json,re
from pathlib import Path
text=Path("Packages").read_text(encoding="utf-8",errors="replace")
records=[]
for stanza in re.split(r"\n\s*\n",text.strip()):
    if not stanza.strip(): continue
    fields={}
    current=None
    for line in stanza.splitlines():
        if line.startswith((" ","\t")) and current:
            fields[current]+=" "+line.strip()
        elif ": " in line:
            current,value=line.split(": ",1); fields[current]=value
    if fields.get("Package"): records.append(fields)
names={x["Package"] for x in records}
provided=set()
for item in records:
    for value in item.get("Provides","").split(","):
        match=re.match(r"\s*([a-z0-9][a-z0-9+.-]*)",value)
        if match: provided.add(match.group(1))
available=names|provided
results=[]
for item in records:
    dependencies=[]
    for field in ("Pre-Depends","Depends"):
        raw=item.get(field,"")
        if not raw: continue
        for group in raw.split(","):
            alternatives=[]
            for alt in group.split("|"):
                match=re.match(r"\s*([a-z0-9][a-z0-9+.-]*)",alt)
                if match: alternatives.append(match.group(1))
            if not alternatives: continue
            resolved=any(x in available for x in alternatives)
            dependencies.append({"field":field,"alternatives":alternatives,"status":"in-repository" if resolved else "external-or-virtual"})
    results.append({"package":item["Package"],"version":item.get("Version",""),"dependencies":dependencies})
out={"scope":"Repository-local dependency presence only; external dependencies are not proof of missing packages.","packages":results,"summary":{"packageCount":len(results),"dependencyGroups":sum(len(x["dependencies"]) for x in results),"inRepository":sum(d["status"]=="in-repository" for x in results for d in x["dependencies"]),"externalOrVirtual":sum(d["status"]=="external-or-virtual" for x in results for d in x["dependencies"]) }}
Path(".github/audit/dependency-audit.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("Dependency audit: "+json.dumps(out["summary"],ensure_ascii=False))
