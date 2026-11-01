#!/usr/bin/env bash
# install-into-repo.sh [--src <dir|url>] [target]
#
# Copies this repo's skills/, scripts/, roles/ and agents/ into
# <target>/.claude/ so Claude Code loads them as *project* skills:
# /vk-implement, /vk-consult, /vk-coding-style, ... Every `/vk-` handoff in every copied
# file (skills, scripts, roles, agents) is rewritten to `/vk-` to match. Running it twice on the same
# target changes nothing (it wipes its own previous copy first).
#
# The skills in UNPREFIXED_SKILLS keep their bare name (.claude/skills/steward,
# /steward): a host looks for them under that exact path. Each carries a
# .vk-installed marker; a directory of that name without the marker is
# someone else's and is left alone.
#
# Targets bash 3.2 (macOS default): no arrays, no `[[ ]]`, no GNU-only flags -
# the macOS floor. `sed -i` is not portable between BSD and GNU,
# so every rewrite here goes through a temp file + `mv` instead.
set -uo pipefail

SELF="$0"
SCRIPT_DIR=$(CDPATH= cd "$(dirname "$SELF")" 2>/dev/null && pwd)
SELF_ABS="$SCRIPT_DIR/$(basename "$SELF")"

DEFAULT_SRC_URL="https://github.com/vkrepkiy/claude-skill-task.git"
DEFAULT_SRC_REPO="vkrepkiy/claude-skill-task"

UNPREFIXED_SKILLS="steward"
MARKER=".vk-installed"

warn() { printf '[install-into-repo] WARN: %s\n' "$*" >&2; }

# die <exit-code> <message>
die() {
  printf 'INSTALL_ERROR(%s): %s\n' "$1" "$2" >&2
  exit "$1"
}

usage() {
  cat <<'USAGE'
install-into-repo.sh [--src <dir|url>] [target]

  --src <dir|url>   where to copy the plugin from. A directory is used in
                     place; anything else is `git clone --depth 1` into a
                     scratch dir that is removed on exit. Defaults to
                     $VK_SRC, then the upstream repo over https.
  target            the repo to install into. Defaults to the git toplevel
                     of the current directory. Refused if it is not a git
                     repo, or if it is this plugin's own checkout.

Copies skills/, scripts/, roles/ and agents/vk-*.md into <target>/.claude/,
as skills/vk-<name> (skills/steward keeps its bare name), rewrites every `/vk-` handoff to `/vk-` in every copied file, stamps
.claude/vk-version, and leaves a copy of itself at .claude/vk-update.sh so the
install can be re-run later. Never commits - it prints the git command to run.
USAGE
}

# ------------------------------------------------------------- arg parsing ---

SRC=""
TARGET=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --src)
      [ "$#" -ge 2 ] || die 2 "--src requires a value"
      SRC="$2"
      shift 2
      ;;
    --src=*)
      SRC="${1#--src=}"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    -*)
      die 2 "unknown option: $1"
      ;;
    *)
      [ -z "$TARGET" ] || die 2 "unexpected extra argument: $1"
      TARGET="$1"
      shift
      ;;
  esac
done

# ------------------------------------------------------------------ target ---

if [ -n "$TARGET" ]; then
  [ -d "$TARGET" ] || die 2 "target is not a directory: $TARGET"
  TARGET=$(CDPATH= cd "$TARGET" 2>/dev/null && pwd) || die 2 "cannot resolve target path: $TARGET"
else
  TARGET=$(pwd)
fi

TARGET=$(git -C "$TARGET" rev-parse --show-toplevel 2>/dev/null) || die 2 "target is not a git repo: $TARGET"

is_own_checkout() {
  local dir="$1" f
  for f in "$dir/plugin.json" "$dir/.claude-plugin/plugin.json"; do
    [ -f "$f" ] || continue
    LC_ALL=C grep -q '"name"[[:space:]]*:[[:space:]]*"vk"' "$f" 2>/dev/null && return 0
  done
  return 1
}

is_own_checkout "$TARGET" && die 2 "target is this plugin's own checkout (plugin.json name \"vk\"): $TARGET"

# ------------------------------------------------------------------ source ---

[ -n "$SRC" ] || SRC="${VK_SRC:-}"
[ -n "$SRC" ] || SRC="$DEFAULT_SRC_URL"

CLONE_DIR=""
cleanup() { [ -z "$CLONE_DIR" ] || rm -rf "$CLONE_DIR"; }
trap cleanup EXIT

if [ -d "$SRC" ]; then
  SRC_DIR=$(CDPATH= cd "$SRC" 2>/dev/null && pwd) || die 2 "cannot resolve source directory: $SRC"
else
  command -v git >/dev/null 2>&1 || die 2 "git is required to clone source: $SRC"
  CLONE_DIR=$(mktemp -d) || die 5 "mktemp failed"
  printf 'CLONING: %s\n' "$SRC"
  # The upstream repo is private. `gh` carries a GitHub credential that plain
  # git often lacks (an ssh-only machine has no https helper, and `git clone`
  # over https then prompts for a username or dies with "Device not
  # configured"). So for the default source prefer `gh repo clone` whenever gh
  # is present and logged in; everything else, and any explicit --src URL, goes
  # through git as given.
  if [ "$SRC" = "$DEFAULT_SRC_URL" ] && command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
    gh repo clone "$DEFAULT_SRC_REPO" "$CLONE_DIR" -- --depth 1 --quiet || die 2 "gh repo clone failed: $DEFAULT_SRC_REPO"
  else
    git clone --depth 1 --quiet "$SRC" "$CLONE_DIR" || die 2 "git clone failed: $SRC (private repo: log in with gh, or pass --src <local checkout>)"
  fi
  SRC_DIR="$CLONE_DIR"
fi

[ -d "$SRC_DIR/skills" ] || die 2 "source has no skills/ directory: $SRC_DIR"

src_version() {
  local f v
  for f in "$SRC_DIR/plugin.json" "$SRC_DIR/.claude-plugin/plugin.json"; do
    [ -f "$f" ] || continue
    v=$(LC_ALL=C sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$f" | head -n1)
    [ -z "$v" ] || { printf '%s\n' "$v"; return 0; }
  done
  printf 'unknown\n'
}

VERSION=$(src_version)
SHA=$(git -C "$SRC_DIR" rev-parse --short HEAD 2>/dev/null)
[ -n "$SHA" ] || SHA="local"

# -------------------------------------------------------------- install ---

CLAUDE_DIR="$TARGET/.claude"
mkdir -p "$CLAUDE_DIR" || die 5 "cannot create $CLAUDE_DIR"

# A target that already has .claude/scripts or .claude/roles but no
# .claude/vk-version stamp got that content from somewhere else - most likely
# the target repo's own hooks/scripts, not a previous run of this installer.
# Refuse rather than silently rm -rf someone else's files.
guard_foreign() {
  local path="$1" label="$2"
  if [ -e "$path" ] && [ ! -f "$CLAUDE_DIR/vk-version" ]; then
    die 2 "$label exists but there is no .claude/vk-version stamp, so this does not look like a previous install - refusing to overwrite it. Remove or move it yourself first if that's really unused."
  fi
}
guard_foreign "$CLAUDE_DIR/scripts" ".claude/scripts"
guard_foreign "$CLAUDE_DIR/roles" ".claude/roles"

# Stamp FIRST, as `pending ...`, before anything under .claude/ is created:
# guard_foreign keys on this file's existence, so a run that dies half-way
# must not leave scripts/ behind with no stamp - that would make every later
# run refuse forever. The real line replaces it as the very last write, so a
# stamp without `pending` means the whole install landed.
printf 'pending %s %s %s\n' "$VERSION" "$SHA" "$(date +%Y-%m-%d)" > "$CLAUDE_DIR/vk-version" || die 5 "cannot write vk-version"

# Wipe the previous copy so a re-run never leaves stale files behind.
rm -rf "$CLAUDE_DIR"/skills/vk-* 2>/dev/null
for name in $UNPREFIXED_SKILLS; do
  [ ! -f "$CLAUDE_DIR/skills/$name/$MARKER" ] || rm -rf "$CLAUDE_DIR/skills/$name"
done
rm -rf "$CLAUDE_DIR/scripts"
rm -rf "$CLAUDE_DIR/roles"
if [ -d "$CLAUDE_DIR/agents" ]; then
  find "$CLAUDE_DIR/agents" -maxdepth 1 -type f -name 'vk-*.md' -exec rm -f {} +
fi

is_unprefixed() {
  local candidate
  for candidate in $UNPREFIXED_SKILLS; do
    [ "$candidate" != "$1" ] || return 0
  done
  return 1
}

# `/vk[:]steward` -> `/steward` for every unprefixed skill, applied before the
# general `/vk[:]` -> `/vk-` rewrite.
UNPREFIXED_SED=""
for name in $UNPREFIXED_SKILLS; do
  UNPREFIXED_SED="$UNPREFIXED_SED s#/vk[:]$name#/$name#g;"
done

# rewrite_vk <file> [bare-skill-name] - portable stand-in for `sed -i`.
# Every text file we copy gets `/vk-` -> `/vk-`: skill bodies and the
# agent/role prose. The pattern is
# spelled `/vk[:]` so that the installed copy of this script - which is
# rewritten too - keeps a working pattern. Written back with `cat >` so the
# file keeps its mode (scripts must stay executable).
rewrite_vk() {
  local f="$1" name="${2:-}" tmp
  tmp="$f.vktmp.$$"
  if [ -n "$name" ]; then
    LC_ALL=C sed -e "s/^name: $name\$/name: vk-$name/" -e "$UNPREFIXED_SED" -e 's#/vk[:]#/vk-#g' "$f" > "$tmp"
  else
    LC_ALL=C sed -e "$UNPREFIXED_SED" -e 's#/vk[:]#/vk-#g' "$f" > "$tmp"
  fi && cat "$tmp" > "$f"
  rm -f "$tmp"
}

mkdir -p "$CLAUDE_DIR/skills" || die 5 "cannot create $CLAUDE_DIR/skills"

N=0
for d in "$SRC_DIR"/skills/*/; do
  [ -d "$d" ] || continue
  name=$(basename "$d")
  if is_unprefixed "$name"; then
    dest="$CLAUDE_DIR/skills/$name"
    rename=""
    if [ -e "$dest" ]; then
      warn ".claude/skills/$name exists and was not installed by vk - left alone, $name not installed"
      continue
    fi
  else
    dest="$CLAUDE_DIR/skills/vk-$name"
    rename="$name"
  fi
  rm -rf "$dest"
  mkdir -p "$dest" || die 5 "cannot create $dest"
  cp -R "$d." "$dest/" || die 5 "cannot copy $d to $dest"
  rm -f "$dest/agents/openai.yaml"
  find "$dest" -type f -name '*.md' -print | while IFS= read -r f; do
    rewrite_vk "$f" "$rename"
  done
  if is_unprefixed "$name"; then
    printf 'installed by vk; replaced by .claude/vk-update.sh\n' > "$dest/$MARKER" || die 5 "cannot write $dest/$MARKER"
  fi
  N=$((N + 1))
done

rm -rf "$CLAUDE_DIR/scripts"
mkdir -p "$CLAUDE_DIR/scripts" || die 5 "cannot create $CLAUDE_DIR/scripts"
cp -R "$SRC_DIR/scripts/." "$CLAUDE_DIR/scripts/" || die 5 "cannot copy scripts/"
find "$CLAUDE_DIR/scripts" -type f \( -name '*.sh' -o -name '*.md' \) -print | while IFS= read -r f; do
  rewrite_vk "$f"
done

rm -rf "$CLAUDE_DIR/roles"
mkdir -p "$CLAUDE_DIR/roles" || die 5 "cannot create $CLAUDE_DIR/roles"
cp -R "$SRC_DIR/roles/." "$CLAUDE_DIR/roles/" || die 5 "cannot copy roles/"
find "$CLAUDE_DIR/roles" -type f -name '*.md' -print | while IFS= read -r f; do
  rewrite_vk "$f"
done

mkdir -p "$CLAUDE_DIR/agents" || die 5 "cannot create $CLAUDE_DIR/agents"
for f in "$SRC_DIR"/agents/vk-*.md; do
  [ -f "$f" ] || continue
  cp "$f" "$CLAUDE_DIR/agents/" || die 5 "cannot copy $f"
  rewrite_vk "$CLAUDE_DIR/agents/$(basename "$f")"
done


# Mark the generated paths so GitHub collapses them in review.
append_line() {
  local f="$1" line="$2"
  if [ -f "$f" ] && [ -s "$f" ] && [ "$(tail -c1 "$f" | wc -l | tr -d ' ')" = "0" ]; then
    printf '\n' >> "$f" 2>/dev/null || true
  fi
  printf '%s\n' "$line" >> "$f" 2>/dev/null || { warn "cannot write $f"; return 1; }
}

GA="$TARGET/.gitattributes"
GENERATED_LINES='.claude/skills/vk-*/** linguist-generated=true
.claude/scripts/** linguist-generated=true
.claude/roles/** linguist-generated=true
.claude/agents/vk-*.md linguist-generated=true'
for name in $UNPREFIXED_SKILLS; do
  GENERATED_LINES="$GENERATED_LINES
.claude/skills/$name/** linguist-generated=true"
done
printf '%s\n' "$GENERATED_LINES" | while IFS= read -r line; do
  if [ ! -f "$GA" ] || ! grep -qxF "$line" "$GA" 2>/dev/null; then
    append_line "$GA" "$line"
  fi
done

# A global gitignore that ignores `.claude/` (a common Claude Code setting)
# hides the whole install from git: nothing is committed, and a cloud session
# on this repo never sees the skills. Write an un-ignore block only when it is
# actually needed, keep
# `.claude/*` so machine-local files stay out, and re-check afterwards.
# `.claude/work/` is deliberately NOT un-ignored: if the target ignores it,
# agent workspaces stay local there.
GI="$TARGET/.gitignore"
if git -C "$TARGET" check-ignore -q ".claude/vk-version" 2>/dev/null; then
  if ! grep -qxF '!.claude/skills/' "$GI" 2>/dev/null; then
    append_line "$GI" ''
    append_line "$GI" '# vk: the repo-local skill install is committed, so a'
    append_line "$GI" '# cloud session on this repo has them without any setup.'
    grep -qxF '!.claude/' "$GI" 2>/dev/null || append_line "$GI" '!.claude/'
    grep -qxF '.claude/*' "$GI" 2>/dev/null || append_line "$GI" '.claude/*'
    for line in '!.claude/skills/' '!.claude/scripts/' '!.claude/roles/' '!.claude/agents/' '!.claude/vk-version' '!.claude/vk-update.sh'; do
      grep -qxF "$line" "$GI" 2>/dev/null || append_line "$GI" "$line"
    done
    printf 'UNIGNORED: added a .claude/ un-ignore block to .gitignore\n'
  fi
  if git -C "$TARGET" check-ignore -q ".claude/vk-version" 2>/dev/null; then
    warn ".claude/ is STILL ignored after writing .gitignore - the install will not be committed."
    warn "Find the cause with: git -C $TARGET check-ignore -v .claude/vk-version"
  fi
fi

DEST_UPDATE="$CLAUDE_DIR/vk-update.sh"
# Copy from the freshly installed scripts/ copy, not from $SELF_ABS: when this
# runs as .claude/vk-update.sh itself, $SELF_ABS *is* the destination, and a
# skipped or identical copy would pin the updater at the first installed
# version forever. The scripts/ copy was just written from $SRC_DIR, so it is
# the new version by construction and never the same file.
cp "$CLAUDE_DIR/scripts/install-into-repo.sh" "$DEST_UPDATE.new" || die 5 "cannot copy updater to $DEST_UPDATE"
mv "$DEST_UPDATE.new" "$DEST_UPDATE" || die 5 "cannot replace $DEST_UPDATE"
chmod +x "$DEST_UPDATE"

printf '%s %s %s\n' "$VERSION" "$SHA" "$(date +%Y-%m-%d)" > "$CLAUDE_DIR/vk-version" || die 5 "cannot write vk-version"

printf 'INSTALLED: vk %s (%s) -> %s/.claude, %s skills\n' "$VERSION" "$SHA" "$TARGET" "$N"
printf 'git add .claude .gitattributes .gitignore && git commit -m "chore(vk): install skills %s"\n' "$VERSION"
