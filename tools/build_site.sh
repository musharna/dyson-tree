#!/usr/bin/env bash
# Build the GitHub Pages artifact: site/ is exactly what gets published.
#
# An explicit allowlist, not `cp -r web/ site/`. web/ also holds the parity
# harness (parity.mjs) and the 170 KB fixture file, neither of which the page
# loads; a recursive copy would publish both and make the artifact grow
# silently whenever anything lands in web/.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$here"

rm -rf site
mkdir -p site

for f in index.html model.js app.js; do
  test -f "web/$f" || { echo "missing web/$f" >&2; exit 1; }
  cp "web/$f" "site/$f"
done

# The published page is the copy most readers see, and CC-BY requires the
# attribution to travel with the work. Ship both licence texts beside it.
for f in LICENSE LICENSE-docs; do
  test -f "$f" || { echo "missing $f" >&2; exit 1; }
  cp "$f" "site/$f"
done

# Pages runs Jekyll unless told not to; .nojekyll also stops it dropping any
# future underscore-prefixed file.
touch site/.nojekyll

# The page must not reach outside its own directory for anything it LOADS: no
# CDN, no absolute asset paths, no build step. Absolute http(s) links in prose
# are navigation, not assets, and are left alone -- so this checks `src=` (any
# element) and `href=` on <link> only.
if grep -nE 'src="(https?:)?//' site/index.html \
  || grep -nE '<link[^>]+href="(https?:)?//' site/index.html; then
  echo "ERROR: site/index.html loads a remote asset; assets must be relative" >&2
  exit 1
fi

echo "built site/:"
ls -la site/
