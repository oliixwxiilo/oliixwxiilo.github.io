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

raw=index.read_text(encoding="utf-8",errors="surrogateescape")
output=[]
sanitized_count=0
for stanza in re.split(r"\n\s*\n",raw.strip()):
    if not stanza.strip():
        continue
    fields={}
    current=None
    original_lines=stanza.splitlines()
    for line in original_lines:
        if line.startswith((" ",chr(9))) and current:
            fields[current]+="\n"+line[1:]
        elif ": " in line:
            current,value=line.split(": ",1)
            fields[current]=value
    package=fields.get("Package","").strip()
    sanitized={}
    def has_invalid_utf8(value):
        return any("\udc80" <= ch <= "\udcff" for ch in value)
    if has_invalid_utf8(fields.get("Name","")):
        sanitized["Name"]=package
    if has_invalid_utf8(fields.get("Description","")):
        sanitized["Description"]="Package "+package+". See the depiction page for details."
    for key in ("Maintainer","Author"):
        if has_invalid_utf8(fields.get(key,"")):
            sanitized[key]="Unknown (invalid source metadata)"
    sanitized_count+=len(sanitized)
    lines=[]
    current=None
    written=set()
    for line in original_lines:
        if line.startswith((" ",chr(9))) and current:
            if current not in sanitized:
                lines.append(line)
        elif ": " in line:
            current,value=line.split(": ",1)
            if current in sanitized:
                if current not in written:
                    lines.append(current+": "+sanitized[current])
                    written.add(current)
            elif current != "Depiction":
                lines.append(line)
        else:
            lines.append(line)
    package=fields.get("Package","").strip()
    version=fields.get("Version","").strip()
    if not package or not version:
        raise SystemExit("Cannot add Depiction to stanza without Package/Version")
    url=base+"depictions/"+safe_part(package)+"/"+safe_part(version)+"/"
    insert_at=next((i+1 for i,line in enumerate(lines) if line.startswith("Version: ")),len(lines))
    lines.insert(insert_at,"Depiction: "+url)
    output.append("\n".join(lines))
index.write_text("\n\n".join(output)+"\n",encoding="utf-8",errors="surrogateescape")
print("Added stable Depiction URLs to "+str(len(output))+" package entries; sanitized invalid UTF-8 display fields: "+str(sanitized_count)+".")
