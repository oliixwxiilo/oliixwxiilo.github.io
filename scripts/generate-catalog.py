#!/usr/bin/env python3
import json, re, html, hashlib, shutil, subprocess, tempfile
from pathlib import Path
root=Path(__file__).resolve().parent.parent
raw=(root/"Packages").read_text(encoding="utf-8",errors="replace")
audit_path=root/"package-audit.json"
audit_data=json.loads(audit_path.read_text(encoding="utf-8")) if audit_path.exists() else {"packages":[]}
audit_by_file={x["filename"]:x for x in audit_data.get("packages",[])}
config_path=root/"repo-config.json"
config=json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {"packages":{}}
manual=config.get("packages",{})
asset_root=root/"assets"/"packages"
if asset_root.exists(): shutil.rmtree(asset_root)
asset_root.mkdir(parents=True,exist_ok=True)

def safe_part(value):
    value=re.sub(r"[^A-Za-z0-9.+~-]+","-",str(value or "unknown"))
    return value.strip(".-") or "unknown"

def extract_images(deb_path, package, version):
    images=[]
    if not deb_path.is_file(): return images
    with tempfile.TemporaryDirectory(prefix="repo-deb-") as tmp:
        result=subprocess.run(["dpkg-deb","-x",str(deb_path),tmp],capture_output=True,text=True)
        if result.returncode:
            print("WARNING: image extraction failed for "+deb_path.name)
            return images
        candidates=[]
        for path in Path(tmp).rglob("*"):
            if not path.is_file() or path.is_symlink() or path.suffix.lower() not in {".png",".jpg",".jpeg",".webp",".gif"}: continue
            try:
                size=path.stat().st_size
                if size<=0 or size>2*1024*1024: continue
                rel=path.relative_to(tmp).as_posix()
            except OSError: continue
            low=rel.lower()
            if any(x in low for x in ("/.git/","/cache/","/caches/")): continue
            score=100 if any(x in path.name.lower() for x in ("icon","appicon","logo")) else 0
            if any(x in low for x in ("screenshot","preview","demo")): score+=30
            candidates.append((score,rel,path,size))
        candidates.sort(key=lambda x:(-x[0],x[1].lower()))
        dest=asset_root/safe_part(package)/safe_part(version)
        for score,rel,path,size in candidates[:6]:
            digest=hashlib.sha256(path.read_bytes()).hexdigest()[:12]
            dest.mkdir(parents=True,exist_ok=True)
            target=dest/(digest+path.suffix.lower())
            shutil.copyfile(path,target)
            low=rel.lower()
            if any(x in path.name.lower() for x in ("icon","appicon","logo")): kind="icon"
            elif any(x in low for x in ("screenshot","preview","demo")): kind="screenshot"
            else: kind="image"
            images.append({"path":target.relative_to(root).as_posix(),"source":rel,"kind":kind,"size":size})
    return images

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
    audit=audit_by_file.get(filename.removeprefix("./"),{})
    images=extract_images(root/filename.removeprefix("./"),pkg,ver)
    local_icon=next((x["path"] for x in images if x["kind"]=="icon"),"")
    # Filename convention and APT architecture are independent signals.
    editorial=manual.get(pkg,{})
    compatibility=editorial.get("compatibility",{})
    packages.append({
      "package":pkg,"name":name,"version":ver,"architecture":arch,
      "environment":env,"filename":filename.removeprefix("./"),
      "section":fields.get("Section","Other"),"depends":fields.get("Depends",""),
      "description":editorial.get("description") or desc,"summary":editorial.get("summary",""),"author":fields.get("Author",fields.get("Maintainer","")),
      "homepage":editorial.get("homepage",""),"supportUrl":editorial.get("supportUrl",""),
      "ios":editorial.get("ios",{"min":"","max":""}),"compatibility":compatibility,
      "changelog":editorial.get("changelog",[]),
      "icon":local_icon or fields.get("Icon",""),"images":images,"size":fields.get("Size",""),"sha256":fields.get("SHA256",""),
      "review":audit.get("review","not-audited"),"controlDepends":audit.get("depends",fields.get("Depends",""))
    })
packages.sort(key=lambda p:(p["environment"],p["name"].lower(),p["package"],p["version"]))
for p in packages:
    editorial=manual.get(p["package"],{})
    if editorial.get("displayName"):
        p["name"]=editorial["displayName"]
    if editorial.get("icon"):
        p["icon"]=editorial["icon"]
history={}
for p in packages:
    history.setdefault(p["package"],{"package":p["package"],"name":p["name"],"versions":[]})
    history[p["package"]]["versions"].append({
      "version":p["version"],"architecture":p["architecture"],
      "filename":p["filename"],"sha256":p["sha256"],"size":p["size"]
    })
for item in history.values():
    item["versions"].sort(key=lambda x:x["version"],reverse=True)
(root/"version-history.json").write_text(
    json.dumps({"packages":list(history.values())},ensure_ascii=False,indent=2)+"\n",
    encoding="utf-8"
)
(root/"catalog.json").write_text(json.dumps({"repository":"https://oliixwxiilo.github.io/","packages":packages},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
pages=root/"depictions"
for p in packages:
    target=pages/safe_part(p["package"])/safe_part(p["version"])/"index.html"
    target.parent.mkdir(parents=True,exist_ok=True)
    esc=lambda x:html.escape(str(x or ""),quote=True)
    gallery_items=[]
    for item in p["images"]:
        label={"icon":"插件图标","screenshot":"截图 / 预览","image":"插件资源"}[item["kind"]]
        gallery_items.append('<figure><img loading="lazy" src="../../../'+esc(item["path"])+'" alt="'+esc(label)+'"><figcaption>'+esc(label)+'</figcaption></figure>')
    gallery='<div class="gallery">'+''.join(gallery_items)+'</div>' if gallery_items else '<p class="muted">此 DEB 未发现可安全展示的图片资源。</p>'
    target.write_text("""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#101827"><title>"""+esc(p["name"])+""" · Oliixwxiilo Repo</title>
<style>body{margin:0;background:#0b1220;color:#edf3ff;font:16px/1.7 -apple-system,BlinkMacSystemFont,sans-serif}main{max-width:720px;margin:48px auto;padding:20px}.card{background:#121d30;border:1px solid #26364d;border-radius:18px;padding:24px}h1{font-size:30px}.muted{color:#9aabc3}.gallery{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:12px;margin:20px 0}figure{margin:0;background:#0b1423;border:1px solid #26364d;border-radius:12px;padding:10px}figure img{width:100%;height:150px;object-fit:contain}figcaption{font-size:12px;color:#9aabc3;text-align:center}.tag{display:inline-block;border:1px solid #40516a;border-radius:30px;padding:3px 10px;margin:3px;font-size:13px}a{color:#8bb5ff}</style></head><body><main><p><a href="../../../">← 返回软件源</a></p><section class="card"><p class="muted">软件包详情</p><h1>"""+esc(p["name"])+"""</h1><p class="muted">"""+esc(p["package"])+"""</p><span class="tag">"""+esc(p["environment"])+"""</span><span class="tag">"""+esc(p["architecture"])+"""</span><span class="tag">版本 """+esc(p["version"])+"""</span><p>"""+esc(p["description"] or "暂无详细介绍。") +"""</p>""" + gallery + """<hr><p><b>作者：</b>"""+esc(p["author"] or "未提供")+"""</p><p><b>分类：</b>"""+esc(p["section"])+"""</p><p><b>依赖：</b>"""+esc(p["depends"] or "未提供")+"""</p><p><b>DEB：</b>"""+esc(p["filename"])+"""</p><p><b>兼容性审核：</b>""" + esc(p["review"]) + """</p><p class="muted">图片从 DEB 内部常见栅格图像资源提取；兼容性仍需在目标越狱环境实际验证。</p></section></main></body></html>""",encoding="utf-8")
print(f"Generated catalog for {len(packages)} package versions and depiction pages.")
