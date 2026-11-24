#!/usr/bin/env python3
"""Add stable HTML depiction URLs to every generated APT package stanza."""
import re
from pathlib import Path

root=Path(__file__).resolve().parent.parent
index=root/"Packages"
base="https://oliixwxiilo.github.io/"

def safe_part(value):
    value=re.sub(r"[^A-Za-z0-9.+~-]+","-",str(value or "unknown"))
    return value.strip(".-") or "unknown"

raw=index.read_text(encoding="utf-8")
output=[]
for stanza in re.split(r"\n\s*\n",raw.strip()):
    if not stanza.strip():
        continue
    fields={}
    current=None
    lines=[]
    for line in stanza.splitlines():
        if line.startswith((" ",chr(9))) and current:
            fields[current]+="\n"+line[1:]
        elif ": " in line:
            current,value=line.split(": ",1)
            fields[current]=value
        if not line.startswith("Depiction: "):
            lines.append(line)
    package=fields.get("Package","").strip()
    version=fields.get("Version","").strip()
    if not package or not version:
        raise SystemExit("Cannot add Depiction to stanza without Package/Version")
    url=base+"depictions/"+safe_part(package)+"/"+safe_part(version)+"/"
    insert_at=next((i+1 for i,line in enumerate(lines) if line.startswith("Version: ")),len(lines))
    lines.insert(insert_at,"Depiction: "+url)
    output.append("\n".join(lines))
index.write_text("\n\n".join(output)+"\n",encoding="utf-8")
print("Added stable Depiction URLs to "+str(len(output))+" package entries.")
