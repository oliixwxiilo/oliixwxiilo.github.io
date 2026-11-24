#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
BASE_REF="${BASE_REF:-origin/main}"
git rev-parse --verify "$BASE_REF" >/dev/null 2>&1 || { echo "Missing comparison ref: $BASE_REF" >&2; exit 1; }
tmp_base="$(mktemp)"
tmp_head="$(mktemp)"
trap 'rm -f "$tmp_base" "$tmp_head"' EXIT
git ls-tree -r --name-only "$BASE_REF" | grep -E "\\.deb$" | while IFS= read -r file; do
  git show "$BASE_REF:$file" | sha256sum | awk '{print $1}'
done | sort > "$tmp_base"
find debs -type f -name "*.deb" -print0 | sort -z | while IFS= read -r -d "" file; do
  sha256sum "$file" | awk '{print $1}'
done | sort > "$tmp_head"
if ! cmp -s "$tmp_base" "$tmp_head"; then
  echo "Release blocked: DEB content set differs from production baseline." >&2
  echo "All original DEB bytes must be preserved exactly during directory migration." >&2
  exit 1
fi
python3 - <<'PY'
import json
from pathlib import Path
cfg=json.loads(Path("repo-config.json").read_text(encoding="utf-8"))
if cfg.get("repository") != "https://oliixwxiilo.github.io/":
    raise SystemExit("Release blocked: canonical repository URL changed")
PY
echo "Release safety passed: all existing DEB files and hashes are preserved."
