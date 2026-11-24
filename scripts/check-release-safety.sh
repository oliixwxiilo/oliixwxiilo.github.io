#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
BASE_REF="${BASE_REF:-origin/main}"
git rev-parse --verify "$BASE_REF" >/dev/null 2>&1 || { echo "Missing comparison ref: $BASE_REF" >&2; exit 1; }
tmp_base="$(mktemp)"
tmp_head="$(mktemp)"
trap 'rm -f "$tmp_base" "$tmp_head"' EXIT
git ls-tree -r --name-only "$BASE_REF" | grep -E '\.deb$' | sort > "$tmp_base" || true
find . -maxdepth 1 -type f -name '*.deb' -printf '%f\n' | sort > "$tmp_head"
missing="$(comm -23 "$tmp_base" "$tmp_head" || true)"
if [[ -n "$missing" ]]; then
  echo "Release blocked: existing DEB files are missing:" >&2
  echo "$missing" >&2
  exit 1
fi
while IFS= read -r file; do
  [[ -n "$file" ]] || continue
  if git cat-file -e "$BASE_REF:$file" 2>/dev/null; then
    old_hash="$(git show "$BASE_REF:$file" | sha256sum | awk '{print $1}')"
    new_hash="$(sha256sum "$file" | awk '{print $1}')"
    if [[ "$old_hash" != "$new_hash" ]]; then
      echo "Release blocked: existing DEB content changed: $file" >&2
      exit 1
    fi
  fi
done < "$tmp_base"
python3 - <<'PY'
import json
from pathlib import Path
cfg=json.loads(Path("repo-config.json").read_text(encoding="utf-8"))
if cfg.get("repository") != "https://oliixwxiilo.github.io/":
    raise SystemExit("Release blocked: canonical repository URL changed")
PY
echo "Release safety passed: all existing DEB files and hashes are preserved."
