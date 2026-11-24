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
for stanza in stanzas:
    fields = dict(re.findall(r"^([A-Za-z0-9-]+):\s*(.*)$", stanza, re.M))
    for key in ("Package", "Version", "Architecture", "Filename", "Size", "SHA256"):
        if key not in fields:
            raise SystemExit(f"Package stanza missing {key}: {fields.get('Package', '<unknown>')}")
    path = Path(fields["Filename"].removeprefix("./"))
    if not path.is_file():
        missing.append(str(path))
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
catalog = Path("catalog.json")
if not catalog.is_file():
    raise SystemExit("Missing generated catalog.json")
data = __import__("json").loads(catalog.read_text(encoding="utf-8"))
items = data.get("packages", [])
if len(items) != len(stanzas):
    raise SystemExit("Catalog entry count mismatch: " + str(len(items)) + " vs " + str(len(stanzas)))
for item in items:
    page = Path("depictions") / item["package"] / item["version"] / "index.html"
    if not page.is_file():
        raise SystemExit("Missing depiction page: " + str(page))
print("Validated " + str(len(stanzas)) + " package entries, catalog records and depiction pages.")
PY
