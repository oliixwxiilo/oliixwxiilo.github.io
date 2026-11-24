#!/usr/bin/env python3
"""Inspect every categorized DEB using dpkg-deb and compare with Packages."""
import hashlib, json, re, subprocess
from pathlib import Path
root=Path(__file__).resolve().parent.parent
index=(root/"Packages").read_text(encoding="utf-8",errors="replace")
records={}
for stanza in re.split(r"\n\s*\n",index.strip()):
    fields={}
    for line in stanza.splitlines():
        if line.startswith((" ","\t")): continue
        if ": " in line:
            k,v=line.split(": ",1); fields[k]=v
    if fields.get("Filename"):
        records[fields["Filename"].removeprefix("./")]=fields
(root/".github"/"audit").mkdir(parents=True,exist_ok=True)
results=[]
for deb in sorted((root/"debs").rglob("*.deb")):
    rel=deb.relative_to(root).as_posix()
    proc=subprocess.run(["dpkg-deb","-f",str(deb)],capture_output=True,text=True)
    if proc.returncode:
        raise SystemExit("Cannot read DEB control metadata: "+rel+"\n"+proc.stderr)
    control={}
    current=None
    for line in proc.stdout.splitlines():
        if line.startswith((" ","\t")) and current:
            control[current]+="\n"+line[1:]
        elif ": " in line:
            current,value=line.split(": ",1); control[current]=value
    digest=hashlib.sha256(deb.read_bytes()).hexdigest()
    indexed=records.get(rel)
    if not indexed:
        raise SystemExit("DEB missing from Packages index: "+rel)
    for field in ("Package","Version","Architecture"):
        if control.get(field)!=indexed.get(field):
            raise SystemExit("DEB/index mismatch for "+rel+" field "+field)
    if indexed.get("SHA256") and indexed["SHA256"]!=digest:
        raise SystemExit("SHA256 mismatch for "+rel)
    low=rel.lower()
    if low.endswith("-rootless.deb"):
        env="Rootless"; expected="iphoneos-arm64"
    elif low.endswith("-roothide.deb"):
        env="RootHide"; expected="iphoneos-arm64e"
    else:
        env="待核实"; expected=None
    arch=control.get("Architecture","")
    if expected is None:
        review="filename-environment-unknown"
    elif arch==expected:
        review="filename-and-architecture-consistent; jailbreak compatibility not proven"
    else:
        review="filename-and-architecture-conflict; manual review required"
    results.append({
      "filename":rel,"package":control.get("Package",""),"version":control.get("Version",""),
      "architecture":arch,"environmentHint":env,"depends":control.get("Depends",""),
      "sha256":digest,"size":deb.stat().st_size,"review":review
    })
extra=set(records)-{x["filename"] for x in results}
if extra:
    raise SystemExit("Indexed DEB file missing from repository: "+", ".join(sorted(extra)))
(root/".github"/"audit"/"package-audit.json").write_text(json.dumps({"checks":"dpkg-deb control fields and SHA256 compared with Packages","packages":results},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("Audited "+str(len(results))+" DEB files against Packages.")
