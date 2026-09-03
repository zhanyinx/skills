#!/usr/bin/env bash
#
# Point the invoked copies of this repo's skills at the repository text.
#
# Skills are invoked through ~/.claude/skills/<name>, which symlinks into
# ~/.agents/skills/<name>. This script replaces each of those install-side
# entries with a symlink to this repository's skills/<name>, so there is exactly
# one text per skill and an edit committed here is the edit that runs — no copy
# step on any release.
#
# Idempotent: re-running is a no-op. A real directory found in place is moved
# aside to <name>.pre-link-backup rather than deleted, so nothing is lost.
#
# Usage:
#   scripts/link-skills.sh [--dry-run]
#
# Environment:
#   AGENT_SKILLS_DIR   install location to link into (default ~/.agents/skills)

set -euo pipefail

dry_run=false
case "${1:-}" in
  --dry-run) dry_run=true ;;
  "") ;;
  *) echo "usage: $0 [--dry-run]" >&2; exit 64 ;;
esac

script_dir=$(cd "$(dirname "$0")" && pwd -P)
repo_root=$(cd "$script_dir/.." && pwd -P)
install_dir=${AGENT_SKILLS_DIR:-$HOME/.agents/skills}

echo "repository: $repo_root"
echo "installing into: $install_dir"
$dry_run && echo "(dry run — nothing will be changed)"
echo

run() {
  if $dry_run; then
    echo "    would run: $*"
  else
    "$@"
  fi
}

$dry_run || mkdir -p "$install_dir"

status=0
for source_path in "$repo_root"/skills/*; do
  [ -d "$source_path" ] || continue
  name=$(basename "$source_path")
  target="$install_dir/$name"

  if [ ! -f "$source_path/SKILL.md" ]; then
    echo "!!  $name — no SKILL.md in $source_path, skipped"
    status=1
    continue
  fi

  if [ -L "$target" ]; then
    current=$(cd "$(dirname "$target")" && cd "$(readlink "$target")" 2>/dev/null && pwd -P) || current=""
    if [ "$current" = "$source_path" ]; then
      echo "ok  $name — already linked to the repository"
      continue
    fi
    echo "--> $name — relinking (was $(readlink "$target"))"
    run rm "$target"
  elif [ -d "$target" ]; then
    backup="$target.pre-link-backup"
    if [ -e "$backup" ]; then
      echo "!!  $name — $backup already exists; move or remove it first"
      status=1
      continue
    fi
    echo "--> $name — installed copy moved aside to $(basename "$backup")"
    run mv "$target" "$backup"
  elif [ -e "$target" ]; then
    echo "!!  $name — $target exists and is neither a symlink nor a directory, skipped"
    status=1
    continue
  else
    echo "--> $name — linking for the first time"
  fi

  run ln -s "$source_path" "$target"
done

echo
if [ "$status" -ne 0 ]; then
  echo "Finished with warnings — see the !! lines above." >&2
elif $dry_run; then
  echo "Dry run only. Re-run without --dry-run to point the invoked skills at $repo_root/skills."
else
  echo "Done. The invoked skills now resolve to $repo_root/skills."
fi
exit "$status"
