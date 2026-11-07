#!/usr/bin/env bash
# Copy the live dux-menu files from this machine into the repo.
# Run it after changing the installed files; it never commits or pushes.
#
#   ./sync.sh

set -euo pipefail

REPO=$(cd "$(dirname "$(readlink -f "$0")")" && pwd)

# live file -> path in the repo (keep in sync with install.sh)
FILES=(
	"$HOME/.local/bin/dux-menu:bin/dux-menu"
	"$HOME/.config/hypr/custom/binds.lua:hypr/binds.lua"
)

changed=0
for pair in "${FILES[@]}"; do
	src=${pair%%:*}
	dst="$REPO/${pair#*:}"
	if [ ! -f "$src" ]; then
		echo "missing: $src (skipped)" >&2
		continue
	fi
	if cmp -s "$src" "$dst"; then
		echo "unchanged: ${pair#*:}"
	else
		mkdir -p "$(dirname "$dst")"
		cp "$src" "$dst"
		echo "updated:   ${pair#*:}"
		changed=1
	fi
done

chmod +x "$REPO/bin/dux-menu"

if [ $changed -eq 1 ]; then
	echo
	git -C "$REPO" status --short
	echo
	echo "Review with: git -C \"$REPO\" diff"
fi
