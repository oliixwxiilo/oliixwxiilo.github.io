#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
for f in Packages Packages.gz Release; do
  test -s "$f" || { echo "Missing or empty: $f" >&2; exit 1; }
done
gzip -t Packages.gz
tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT
gzip -dc Packages.gz > "$tmp"
cmp -s Packages "$tmp" || { echo "Packages.gz does not match Packages" >&2; exit 1; }
python3 - <<'PY'
from pathlib import Path
import re
text = Path("Packages").read_text(encoding="utf-8", errors="replace")
stanzas = [s for s in re.split(r"\n\s*\n", text.strip()) if s.strip()]
if not stanzas:
    raise SystemExit("Packages index has no package entries")
missing = []
index_by_identity = {}
for stanza in stanzas:
    fields = dict(re.findall(r"^([A-Za-z0-9-]+):\s*(.*)$", stanza, re.M))
    for key in ("Package", "Version", "Architecture", "Filename", "Size", "SHA256"):
        if key not in fields:
            raise SystemExit(f"Package stanza missing {key}: {fields.get('Package', '<unknown>')}")
    index_by_identity[(fields["Package"],fields["Version"])] = fields
    expected_depiction="https://oliixwxiilo.github.io/depictions/"+re.sub(r"[^A-Za-z0-9.+~-]+", "-", fields["Package"]).strip(".-")+"/"+re.sub(r"[^A-Za-z0-9.+~-]+", "-", fields["Version"]).strip(".-")+"/"
    if fields.get("Depiction") != expected_depiction:
        raise SystemExit("Missing or invalid package-manager Depiction URL: " + fields["Package"])
    filename = fields["Filename"].removeprefix("./")
    path = Path(filename)
    if path.is_absolute() or ".." in path.parts or len(path.parts) != 1 or path.suffix.lower() != ".deb":
        raise SystemExit("Unsafe or non-root DEB filename: " + fields["Filename"])
    if not path.is_file():
        missing.append(str(path))
    digest = __import__("hashlib").sha256(path.read_bytes()).hexdigest()
    if digest.lower() != fields["SHA256"].lower():
        raise SystemExit("DEB SHA256 mismatch: " + filename)
    if path.stat().st_size != int(fields["Size"]):
        raise SystemExit("DEB size mismatch: " + filename)
if missing:
    raise SystemExit("Missing package files:\n" + "\n".join(missing))
audit = Path("package-audit.json")
if not audit.is_file():
    raise SystemExit("Missing DEB audit report")
audit_data = __import__("json").loads(audit.read_text(encoding="utf-8"))
audit_items = audit_data.get("packages", [])
if len(audit_items) != len(stanzas):
    raise SystemExit("DEB audit count mismatch: " + str(len(audit_items)) + " vs " + str(len(stanzas)))
for item in audit_items:
    if item.get("review") == "filename-and-architecture-conflict; manual review required":
        print("WARNING: manual compatibility review required for " + item.get("filename", "<unknown>"))
config_path = Path("repo-config.json")
if not config_path.is_file():
    raise SystemExit("Missing repo-config.json")
config_data = __import__("json").loads(config_path.read_text(encoding="utf-8"))
if config_data.get("schemaVersion") != 1 or not isinstance(config_data.get("packages"), dict):
    raise SystemExit("Invalid repo-config.json schema")
known_packages={match.group(1).strip() for stanza in stanzas for match in [re.search(r"^Package:\s*(.+)$", stanza, re.M)] if match}
for package_id, metadata in config_data["packages"].items():
    if package_id == "_example.package":
        continue
    if package_id not in known_packages:
        raise SystemExit("Metadata references unknown package: " + package_id)
    if not isinstance(metadata, dict):
        raise SystemExit("Package metadata must be an object: " + package_id)
    compatibility=metadata.get("compatibility", {})
    if not isinstance(compatibility, dict):
        raise SystemExit("Invalid compatibility metadata: " + package_id)
    for key in ("rootless", "roothide"):
        status=compatibility.get(key, "unknown")
        if status not in ("unknown", "tested", "not-tested", "partial"):
            raise SystemExit("Invalid " + key + " test status for " + package_id)
    for key in ("homepage", "supportUrl"):
        url=metadata.get(key, "")
        if url and (not isinstance(url, str) or not url.startswith("https://")):
            raise SystemExit("Only verified HTTPS URLs are allowed for " + package_id + " " + key)
catalog = Path("catalog.json")
if not catalog.is_file():
    raise SystemExit("Missing generated catalog.json")
data = __import__("json").loads(catalog.read_text(encoding="utf-8"))
items = data.get("packages", [])
if len(items) != len(stanzas):
    raise SystemExit("Catalog entry count mismatch: " + str(len(items)) + " vs " + str(len(stanzas)))
for item in items:
    for asset in item.get("images", []):
        asset_path = Path(asset.get("path", ""))
        if asset_path.is_absolute() or ".." in asset_path.parts or not asset_path.is_file():
            raise SystemExit("Missing or unsafe package image asset: " + str(asset_path))
    safe_part=lambda value: re.sub(r"[^A-Za-z0-9.+~-]+", "-", str(value or "unknown")).strip(".-") or "unknown"
    page = Path("depictions") / safe_part(item["package"]) / safe_part(item["version"]) / "index.html"
    expected_url="depictions/"+safe_part(item["package"])+"/"+safe_part(item["version"])+"/"
    if item.get("detailUrl") != expected_url:
        raise SystemExit("Invalid detail URL for " + item["package"])
    if not page.is_file():
        raise SystemExit("Missing depiction page: " + str(page))
    page_html=page.read_text(encoding="utf-8",errors="replace")
    expected_download="../../../"+item["filename"]
    if 'href="'+expected_download+'" download' not in page_html:
        raise SystemExit("Depiction download link does not match DEB: " + item["package"])
    indexed=index_by_identity.get((item["package"],item["version"]), {})
    if item.get("sha256") != indexed.get("SHA256") or item.get("filename") != indexed.get("Filename","").removeprefix("./") or str(item.get("size")) != indexed.get("Size"):
        raise SystemExit("Catalog SHA256 does not match Packages: " + item["package"])
# Package identity must be unique for each version and architecture.
identities=set()
filenames=set()
for item in items:
    identity=(item["package"],item["version"],item["architecture"])
    if identity in identities:
        raise SystemExit("Duplicate package/version/architecture: " + repr(identity))
    identities.add(identity)
    if item["filename"] in filenames:
        raise SystemExit("Duplicate DEB filename: " + item["filename"])
    filenames.add(item["filename"])
dependency_audit=Path("dependency-audit.json")
if not dependency_audit.is_file():
    raise SystemExit("Missing dependency-audit.json")
dependency_data=__import__("json").loads(dependency_audit.read_text(encoding="utf-8"))
if len(dependency_data.get("packages",[])) != len(stanzas):
    raise SystemExit("Dependency audit package count mismatch")
history = Path("version-history.json")
if not history.is_file():
    raise SystemExit("Missing version-history.json")
history_data = __import__("json").loads(history.read_text(encoding="utf-8"))
history_items = history_data.get("packages", [])
if len(history_items) != len(set(item["package"] for item in items)):
    raise SystemExit("Version history package count mismatch")
print("Validated " + str(len(stanzas)) + " package entries, unique package identities, dependency audit, catalog, version history and depiction pages.")
PY
