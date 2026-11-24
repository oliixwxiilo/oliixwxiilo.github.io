#!/usr/bin/env python3
import json, re, html
from pathlib import Path
root=Path(__file__).resolve().parent.parent
raw=(root/"Packages").read_text(encoding="utf-8",errors="replace")
packages=[]
for stanza in re.split(r"\n\s*\n",raw.strip()):
    if not stanza.strip(): continue
    fields={}
    for line in stanza.splitlines():
        if line.startswith((" ","\t")): continue
        if ": " in line:
            k,v=line.split(": ",1); fields[k]=v
    pkg=fields.get("Package","")
    ver=fields.get("Version","")
    filename=fields.get("Filename","")
    if not pkg or not ver or not filename: continue
    name=fields.get("Name","").strip()
    # Old index records may contain mojibake. Never publish broken display text.
    def looks_broken(s):
        return "\ufffd" in s or (s and sum(1 for c in s if "\ue000" <= c <= "\uf8ff")/len(s) > .08)
    if not name or looks_broken(name): name=pkg
    desc=fields.get("Description","").split("\n",1)[0].strip()
    if looks_broken(desc): desc=""
    low=filename.lower()
    if "-rootless.deb" in low: env="Rootless"
    elif "-roothide.deb" in low: env="RootHide"
    else: env="待核实"
    arch=fields.get("Architecture","")
    # Filename convention and APT architecture are independent signals.
    packages.append({
      "package":pkg,"name":name,"version":ver,"architecture":arch,
      "environment":env,"filename":filename.removeprefix("./"),
      "section":fields.get("Section","Other"),"depends":fields.get("Depends",""),
      "description":desc,"author":fields.get("Author",fields.get("Maintainer","")),
      "size":fields.get("Size",""),"sha256":fields.get("SHA256","")
    })
packages.sort(key=lambda p:(p["environment"],p["name"].lower(),p["package"],p["version"]))
(root/"catalog.json").write_text(json.dumps({"repository":"https://oliixwxiilo.github.io/","packages":packages},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
pages=root/"depictions"
for p in packages:
    target=pages/p["package"]/p["version"]/"index.html"
    target.parent.mkdir(parents=True,exist_ok=True)
    esc=lambda x:html.escape(str(x or ""),quote=True)
    target.write_text("""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#101827"><title>"""+esc(p["name"])+""" · Oliixwxiilo Repo</title>
<style>body{margin:0;background:#0b1220;color:#edf3ff;font:16px/1.7 -apple-system,BlinkMacSystemFont,sans-serif}main{max-width:720px;margin:48px auto;padding:20px}.card{background:#121d30;border:1px solid #26364d;border-radius:18px;padding:24px}h1{font-size:30px}.muted{color:#9aabc3}.tag{display:inline-block;border:1px solid #40516a;border-radius:30px;padding:3px 10px;margin:3px;font-size:13px}a{color:#8bb5ff}</style></head><body><main><p><a href="../../../..">← 返回软件源</a></p><section class="card"><p class="muted">软件包详情</p><h1>"""+esc(p["name"])+"""</h1><p class="muted">"""+esc(p["package"])+"""</p><span class="tag">"""+esc(p["environment"])+"""</span><span class="tag">"""+esc(p["architecture"])+"""</span><span class="tag">版本 """+esc(p["version"])+"""</span><p>"""+esc(p["description"] or "暂无详细介绍。") +"""</p><hr><p><b>作者：</b>"""+esc(p["author"] or "未提供")+"""</p><p><b>分类：</b>"""+esc(p["section"])+"""</p><p><b>依赖：</b>"""+esc(p["depends"] or "未提供")+"""</p><p><b>DEB：</b>"""+esc(p["filename"])+"""</p><p class="muted">安装前请核对设备越狱类型、系统版本和依赖条件。</p></section></main></body></html>""",encoding="utf-8")
print(f"Generated catalog for {len(packages)} package versions and depiction pages.")
