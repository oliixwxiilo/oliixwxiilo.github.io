#!/usr/bin/env python3
"""Build 丑象派 APT indexes and package depictions from pool/ and metadata/."""
import datetime
import gzip
import hashlib
import html
import json
import lzma
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://oliixwxiilo.github.io"
ARCHES = ("iphoneos-arm64", "iphoneos-arm64e")
FLAT_ARCH = "iphoneos-arm64"
DIST = ROOT / "dists" / "stable"
META_DIR = ROOT / "metadata" / "packages"
DEPICTIONS = ROOT / "depictions"


def parse_control(text):
    fields = {}
    current = None
    for line in text.splitlines():
        if line.startswith((" ", "\t")) and current:
            fields[current] += "\n" + line
        elif ":" in line:
            key, value = line.split(":", 1)
            current = key
            fields[key] = value.lstrip()
    return fields


def load_metadata():
    result = {}
    if not META_DIR.exists():
        return result
    for path in sorted(META_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise SystemExit(f"资料文件无法解析：{path.relative_to(ROOT)}：{exc}")
        package_id = data.get("软件包标识")
        if package_id:
            if package_id in result:
                raise SystemExit(f"软件包标识重复：{package_id}")
            result[package_id] = data
    return result


def public_url(path):
    return BASE_URL + "/" + quote(path.as_posix(), safe="/-._~")


def normalize_icon_key(value):
    """Normalize package/name text so icon matching is case- and punctuation-insensitive."""
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", str(value or "").lower())


def find_package_icon(package_id, control, meta):
    """Find an icon without requiring a per-package JSON file."""
    icon_dir = ROOT / "assets" / "icons"
    if not icon_dir.exists():
        return ""

    # An explicitly configured, existing icon always wins.
    configured = str(meta.get("插件图标") or "").strip()
    if configured and (ROOT / configured).is_file():
        return configured
    if configured:
        print(f"提示：资料中指定的图标不存在，尝试自动匹配：{configured}")

    candidates = [
        package_id,
        package_id.rsplit(".", 1)[-1],
        control.get("Name", ""),
        meta.get("插件名称", ""),
    ]
    keys = []
    for candidate in candidates:
        key = normalize_icon_key(candidate)
        if key and key not in keys:
            keys.append(key)
    if not keys:
        return ""

    extensions = {".png", ".jpg", ".jpeg", ".webp"}
    icons = sorted(
        p for p in icon_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in extensions
    )
    # Exact normalized matches first; package-ID final component supports names
    # such as KillBackground13.png for xyz.cypwn.killbackground13.
    for key in keys:
        matches = [p for p in icons if normalize_icon_key(p.stem) == key]
        if matches:
            selected = matches[0].relative_to(ROOT).as_posix()
            print(f"已自动关联图标：{package_id} -> {selected}")
            return selected
    print(f"提示：没有找到 {package_id} 对应的图标")
    return ""


SECTION_TRANSLATIONS = {
    "Tweaks": "插件",
    "Themes": "主题",
    "Utilities": "实用工具",
    "System": "系统",
    "Networking": "网络",
    "Internet": "网络",
    "Multimedia": "多媒体",
    "Development": "开发工具",
    "Fonts": "字体",
    "Games": "游戏",
    "Ringtones": "铃声",
    "Addons": "附加组件",
    "Accessories": "辅助工具",
    "Productivity": "效率工具",
    "Security": "安全",
    "Repositories": "软件源",
    "Widgets": "小组件",
    "Terminal Support": "终端工具",
    "RootHide": "隐根插件",
    "RootHide Packages": "隐根插件",
    "Rootless": "无根插件",
    "Rootless Packages": "无根插件",
}


def translate_section(value):
    """Localize common package-manager categories while preserving custom sections."""
    section = str(value or "").strip()
    if not section:
        return section
    return SECTION_TRANSLATIONS.get(section, SECTION_TRANSLATIONS.get(section.title(), section))


def format_size(size):
    """Return a compact human-readable package size."""
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.2f} MB"
    if size >= 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size} 字节"


def detected_system(control, meta):
    """Read declared minimum OS compatibility from Debian control metadata."""
    # Explicit JSON compatibility text takes precedence over package control fields.
    configured = str(meta.get("支持的系统") or "").strip()
    if configured:
        return configured
    raw = (
        control.get("Firmware")
        or control.get("MinOSVersion")
        or control.get("MinimumOSVersion")
        or control.get("iOS-Version")
        or control.get("IOS-Version")
        or ""
    ).strip()
    if raw:
        value = raw.replace("iphoneos", "").strip()
        match = re.fullmatch(r"(?:>=|=>)\s*([0-9][0-9.]*)(?:\s*.*)?", value)
        if match:
            return f"iOS {match.group(1)} 及以上"
        match = re.fullmatch(r"([0-9][0-9.]*)", value)
        if match:
            return f"iOS {match.group(1)}"
        return f"iOS 要求：{value}"
    return str(meta.get("支持的系统") or "安装包未注明")


def write_depiction(package_id, control, meta, deb_size):
    folder = DEPICTIONS / package_id
    folder.mkdir(parents=True, exist_ok=True)
    name = meta.get("插件名称") or control.get("Name") or package_id
    version = meta.get("当前版本") or control.get("Version", "")
    description = meta.get("插件介绍") or control.get("Description", "")
    description = description.split("\n", 1)[0].strip()
    upload_date = meta.get("上传日期") or ""
    supported = detected_system(control, meta)
    architecture = control.get("Architecture", "未知")
    package_size = format_size(deb_size)
    icon_path = meta.get("插件图标") or ""
    icon_exists = bool(icon_path and (ROOT / icon_path).is_file())
    if icon_path and not icon_exists:
        print(f"提示：图标尚未上传，暂不加入索引：{icon_path}")
    icon_url = public_url(Path(icon_path)) if icon_exists else control.get("Icon", "")

    detail_views = [
        {"class": "DepictionHeaderView", "title": name},
        {"class": "DepictionMarkdownView", "markdown": description or "暂无介绍"},
        {"class": "DepictionSeparatorView"},
        {"class": "DepictionTableTextView", "title": "当前版本", "text": version},
        {"class": "DepictionTableTextView", "title": "安装包大小", "text": package_size},
        {"class": "DepictionTableTextView", "title": "支持的系统", "text": supported},
        {"class": "DepictionTableTextView", "title": "架构", "text": architecture},
    ]
    if upload_date:
        detail_views.append({"class": "DepictionTableTextView", "title": "上传日期", "text": upload_date})
    older = meta.get("旧版本下载", []) or []
    if older:
        detail_views.append({"class": "DepictionHeaderView", "title": "历史版本"})
        for old in older:
            old_version = old.get("版本", "旧版本")
            old_path = old.get("安装包路径") or old.get("下载路径") or ""
            if old_path and (ROOT / old_path).is_file():
                detail_views.append({
                    "class": "DepictionTableButtonView",
                    "title": f"下载版本 {old_version}",
                    "action": public_url(Path(old_path)),
                    "openExternal": 1
                })
            else:
                print(f"提示：历史版本资料路径不存在，暂不显示下载按钮：{old_path}")

    changelog_views = []
    for entry in meta.get("更新日志", []) or []:
        changelog_views.append({
            "class": "DepictionSubheaderView",
            "title": f"{entry.get('版本', '')}  {entry.get('日期', '')}".strip()
        })
        bullets = entry.get("内容", []) or []
        changelog_views.append({
            "class": "DepictionMarkdownView",
            "markdown": "\n".join(f"- {line}" for line in bullets) if bullets else "暂无更新说明"
        })
    if not changelog_views:
        changelog_views = [{"class": "DepictionMarkdownView", "markdown": "暂无更新日志"}]

    depiction = {
        "minVersion": "0.4",
        "tintColor": "#D65A45",
        "tabs": [
            {"class": "DepictionStackView", "tabname": "详情", "views": detail_views},
            {"class": "DepictionStackView", "tabname": "更新日志", "views": changelog_views}
        ],
        "class": "DepictionTabView"
    }
    if icon_exists:
        depiction["headerImage"] = icon_url
    (folder / "depiction.json").write_text(
        json.dumps(depiction, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )

    changelog_html = ""
    for entry in meta.get("更新日志", []) or []:
        lines = "".join(f"<li>{html.escape(str(x))}</li>" for x in entry.get("内容", []) or [])
        changelog_html += f'<section><h3>{html.escape(str(entry.get("版本", "")))} · {html.escape(str(entry.get("日期", "")))}</h3><ul>{lines}</ul></section>'
    html_doc = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(name)}</title><style>
:root{{color-scheme:light dark}}body{{font-family:-apple-system,BlinkMacSystemFont,sans-serif;max-width:760px;margin:0 auto;padding:24px;line-height:1.65}}
h1{{font-size:28px}}h2{{font-size:20px;border-bottom:1px solid #8885;padding-bottom:8px;margin-top:28px}}
.meta{{display:grid;grid-template-columns:130px 1fr;gap:8px 14px}}.meta b{{opacity:.7}}

section{{border-bottom:1px solid #8885;padding:8px 0}}
</style></head><body><h1>{html.escape(name)}</h1><p>{html.escape(description or "暂无介绍")}</p>
<h2>版本资料</h2><div class="meta">
<b>软件包标识</b><span>{html.escape(package_id)}</span>
<b>当前版本</b><span>{html.escape(version)}</span>
<b>安装包大小</b><span>{html.escape(package_size)}</span>
<b>支持的系统</b><span>{html.escape(supported)}</span>
<b>架构</b><span>{html.escape(architecture)}</span>
<b>上传日期</b><span>{html.escape(upload_date or "未填写")}</span>
</div>
<h2>更新日志</h2>{changelog_html or "<p>暂无更新日志</p>"}
</body></html>"""
    (folder / "index.html").write_text(html_doc, encoding="utf-8")
    depiction_path = folder / "depiction.json"
    depiction_url = public_url(Path("depictions") / package_id / "index.html")
    # Version the native depiction URL by its content hash so Sileo cannot keep
    # showing a stale cached changelog after metadata changes.
    sileo_url = public_url(Path("depictions") / package_id / "depiction.json") + "?v=" + hash_file(depiction_path, "sha256")[:12]
    return icon_url, depiction_url, sileo_url


def hash_file(path, algorithm):
    h = hashlib.new(algorithm)
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def release_text(files, prefix="", architectures=ARCHES):
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    lines = [
        "Origin: 丑象派", "Label: 丑象派", "Suite: stable", "Codename: stable",
        f"Date: {now}", "Architectures: " + " ".join(architectures), "Components: main",
        "Description: Rootless iOS package repository"
    ]
    for algo, label in [("md5", "MD5Sum"), ("sha1", "SHA1"), ("sha256", "SHA256"), ("sha512", "SHA512")]:
        lines.append(label + ":")
        for path, rel in files:
            lines.append(f" {hash_file(path, algo)} {path.stat().st_size} {prefix}{rel}")
    return "\n".join(lines) + "\n"


def main():
    for command in ("dpkg-deb",):
        if subprocess.call(["bash", "-lc", f"command -v {command} >/dev/null 2>&1"]) != 0:
            raise SystemExit(f"缺少 {command}")
    metadata = load_metadata()
    debs = sorted(p for base in (ROOT / "pool" / "main", ROOT / "pool" / "old") if base.exists() for p in base.rglob("*.deb"))
    if not debs:
        raise SystemExit("pool/main 和 pool/old 中没有找到 .deb 安装包")

    records = []
    seen = set()
    for deb in debs:
        raw = subprocess.check_output(["dpkg-deb", "-f", str(deb)], text=True)
        control = parse_control(raw)
        package_id = control.get("Package")
        version = control.get("Version")
        arch = control.get("Architecture")
        if not package_id or not version or not arch:
            raise SystemExit(f"安装包缺少 Package/Version/Architecture：{deb.relative_to(ROOT)}")
        if arch not in (*ARCHES, "all"):
            print(f"跳过不兼容架构：{deb.relative_to(ROOT)} ({arch})")
            continue
        identity = (package_id, version, arch)
        if identity in seen:
            raise SystemExit(f"发现重复的软件包版本：{package_id} {version} {arch}")
        seen.add(identity)
        size = deb.stat().st_size
        # Metadata JSON is optional: construct safe defaults from the Debian control
        # fields, then automatically associate an icon by package ID or display name.
        meta = dict(metadata.get(package_id, {}))
        meta.setdefault("软件包标识", package_id)
        meta.setdefault("插件名称", control.get("Name") or package_id)
        meta.setdefault("当前版本", version)
        icon_path = find_package_icon(package_id, control, meta)
        if icon_path:
            meta["插件图标"] = icon_path
        else:
            meta.pop("插件图标", None)

        depiction_file = DEPICTIONS / package_id / "depiction.json"
        if not depiction_file.exists() or version == str(meta.get("当前版本", "")):
            icon_url, depiction_url, sileo_url = write_depiction(package_id, control, meta, size)
        else:
            icon_path = meta.get("插件图标") or ""
            icon_url = public_url(Path(icon_path)) if icon_path and (ROOT / icon_path).is_file() else control.get("Icon", "")
            depiction_url = public_url(Path("depictions") / package_id / "index.html")
            sileo_url = public_url(Path("depictions") / package_id / "depiction.json") + "?v=" + hash_file(depiction_file, "sha256")[:12]
        fields = dict(control)
        fields["Filename"] = deb.relative_to(ROOT).as_posix()
        fields["Size"] = str(size)
        fields["MD5sum"] = hash_file(deb, "md5")
        fields["SHA1"] = hash_file(deb, "sha1")
        fields["SHA256"] = hash_file(deb, "sha256")
        fields["Name"] = meta.get("插件名称") or fields.get("Name") or package_id
        # Keep the package-list summary consistent with the optional JSON metadata.
        fields["Description"] = meta.get("插件介绍") or fields.get("Description") or ""
        if fields.get("Section"):
            fields["Section"] = translate_section(fields["Section"])
        if icon_url:
            fields["Icon"] = icon_url
        fields["Depiction"] = depiction_url
        fields["SileoDepiction"] = sileo_url
        preferred = ["Package", "Name", "Version", "Architecture", "Description", "Maintainer", "Author", "Section", "Depends", "Filename", "Size", "MD5sum", "SHA1", "SHA256", "Icon", "Depiction", "SileoDepiction"]
        ordered = [k for k in preferred if k in fields] + [k for k in fields if k not in preferred]
        record_lines = []
        for key in ordered:
            value = str(fields[key])
            parts = value.splitlines() or [""]
            record_lines.append(f"{key}: {parts[0]}")
            record_lines.extend(" " + part for part in parts[1:])
        records.append((arch, "\n".join(record_lines)))
        print(f"已索引：{package_id} {version} ({deb.relative_to(ROOT)})")

    if not records:
        raise SystemExit("没有可发布的 iphoneos-arm64、iphoneos-arm64e 或 all 安装包")

    # Build a separate Packages index for each supported architecture.
    # Architecture-independent "all" packages are included in both indexes.
    dist_files = []
    for target_arch in ARCHES:
        arch_records = [record for package_arch, record in records
                        if package_arch in (target_arch, "all")]
        package_data = ("\n\n".join(arch_records) + ("\n\n" if arch_records else "")).encode("utf-8")
        index_dir = DIST / "main" / f"binary-{target_arch}"
        index_dir.mkdir(parents=True, exist_ok=True)
        for filename, payload in (
            ("Packages", package_data),
            ("Packages.gz", gzip.compress(package_data, compresslevel=9, mtime=0)),
            ("Packages.xz", lzma.compress(package_data, format=lzma.FORMAT_XZ, preset=9)),
        ):
            path = index_dir / filename
            path.write_bytes(payload)
            dist_files.append((path, f"main/binary-{target_arch}/{filename}"))
        print(f"已生成 {target_arch} 索引：{len(arch_records)} 条记录")

    # Standard distribution Release includes hashes for both architecture indexes.
    (DIST / "Release").write_text(release_text(dist_files), encoding="utf-8")

    # Flat-repository compatibility files at the web root include both architectures.
    # APT selects packages matching the client's architecture from this combined index.
    flat_records = [record for _, record in records]
    flat_data = ("\n\n".join(flat_records) + ("\n\n" if flat_records else "")).encode("utf-8")
    (ROOT / "Packages").write_bytes(flat_data)
    (ROOT / "Packages.gz").write_bytes(gzip.compress(flat_data, compresslevel=9, mtime=0))
    (ROOT / "Packages.xz").write_bytes(lzma.compress(flat_data, format=lzma.FORMAT_XZ, preset=9))
    flat_files = [(ROOT / f"Packages{suffix}", f"Packages{suffix}") for suffix in ("", ".gz", ".xz")]
    (ROOT / "Release").write_text(release_text(flat_files, "", ARCHES), encoding="utf-8")
    print(f"完成：共读取 {len(records)} 个可发布架构包记录；已生成双架构独立索引和根目录兼容索引。")


if __name__ == "__main__":
    main()
