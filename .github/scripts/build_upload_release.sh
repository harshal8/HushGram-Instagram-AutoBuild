#!/bin/bash
set -euo pipefail

# Unified release uploader using native gh CLI with per-file retry and clobber.
#
# Inputs (via env vars):
#   RELEASE_TAG / TAG     : Release tag name (required)
#   RELEASE_TITLE / TITLE : Release title (default: "Build No. $TAG")
#   RELEASE_BODY_FILE     : Path to markdown notes file (e.g. build.md)
#   RELEASE_NOTES         : Inline release notes string (used if no body file)
#   IS_PRERELEASE         : "true" marks the release a pre-release, "false" marks it
#                           a full release. UNSET/empty means "no opinion": an
#                           existing release keeps whatever state it has, and a new
#                           one is created as non-prerelease (gh's own default).
#                           Anything else is rejected.
#   RELEASE_TARGET        : Target branch/commit for new release (optional, e.g. main)
#   UPDATE_EXISTING_METADATA :
#                           "false" leaves an EXISTING release's title and notes
#                           alone; title/notes then only apply when the release has
#                           to be created. Default: "true"
#   UPLOAD_FILES          : Space-separated files/glob patterns (default: "./build/*")
#   GITHUB_REPOSITORY     : owner/repo (required)
#   GH_TOKEN              : GitHub token (required)
#
# The two metadata knobs are orthogonal: with UPDATE_EXISTING_METADATA=false and
# IS_PRERELEASE unset the uploader writes no metadata at all and skips the edit
# call entirely - a field nobody named is not the uploader's to assert.

TAG="${RELEASE_TAG:-${TAG:?RELEASE_TAG or TAG not set}}"
REPO="${GITHUB_REPOSITORY:?GITHUB_REPOSITORY not set}"
TITLE="${RELEASE_TITLE:-${TITLE:-Build No. $TAG}}"
BODY_FILE="${RELEASE_BODY_FILE:-${BODY_FILE:-}}"
IS_PRERELEASE="${IS_PRERELEASE:-}"
TARGET="${RELEASE_TARGET:-${TARGET:-}}"
FILES_PATTERN="${UPLOAD_FILES:-${FILES:-./build/*}}"
UPDATE_EXISTING_METADATA="${UPDATE_EXISTING_METADATA:-true}"

echo "=== Uploading release assets for tag: $TAG ==="

# 1. Prepare create / edit flags
TARGET_ARG=()
[ -n "$TARGET" ] && TARGET_ARG=(--target "$TARGET")

PRERELEASE_CREATE_ARG=()
PRERELEASE_EDIT_ARG=()
# Three states, because "the caller said nothing" is not the same claim as "the
# caller said false" - the latter used to demote a hand-flagged release silently.
case ${IS_PRERELEASE,,} in
    true)
        PRERELEASE_CREATE_ARG=(--prerelease)
        PRERELEASE_EDIT_ARG=(--prerelease)
        ;;
    false)
        PRERELEASE_EDIT_ARG=(--prerelease=false)
        ;;
    "") ;;
    *)
        echo "::error::IS_PRERELEASE must be true, false or unset (got: '$IS_PRERELEASE')" >&2
        exit 2
        ;;
esac

NOTES_ARG=()
if [ -n "$BODY_FILE" ] && [ -s "$BODY_FILE" ]; then
    NOTES_ARG=(-F "$BODY_FILE")
elif [ -n "${RELEASE_NOTES:-}" ]; then
    NOTES_ARG=(-n "$RELEASE_NOTES")
else
    NOTES_ARG=(-n "")
fi

# 2. Ensure release exists or create it
if gh release view "$TAG" -R "$REPO" >/dev/null 2>&1; then
    # gh release edit replaces the whole body, so an unguarded edit would wipe
    # hand-written archive notes on every build. Assemble only the fields the
    # caller named and write them in one call; no named field, no call.
    EDIT_ARG=()
    [ "$UPDATE_EXISTING_METADATA" = "true" ] && EDIT_ARG+=(-t "$TITLE" "${NOTES_ARG[@]}")
    EDIT_ARG+=("${PRERELEASE_EDIT_ARG[@]}")
    if [ ${#EDIT_ARG[@]} -gt 0 ]; then
        echo "Release $TAG already exists, updating metadata: ${EDIT_ARG[*]}"
        gh release edit "$TAG" "${EDIT_ARG[@]}" -R "$REPO" || true
    else
        echo "Release $TAG already exists and no metadata was named - leaving it as-is."
    fi
else
    echo "Creating release $TAG..."
    gh release create "$TAG" -t "$TITLE" "${NOTES_ARG[@]}" "${PRERELEASE_CREATE_ARG[@]}" "${TARGET_ARG[@]}" -R "$REPO"
fi

# 3. Collect files to upload
shopt -s nullglob
FILES=()
for pattern in $FILES_PATTERN; do
    for f in $pattern; do
        [ -f "$f" ] && FILES+=("$f")
    done
done
shopt -u nullglob

if [ ${#FILES[@]} -eq 0 ]; then
    echo "No files matched '$FILES_PATTERN' to upload"
    exit 0
fi

PARALLEL_JOBS="${UPLOAD_CONCURRENCY:-4}"
echo "Uploading ${#FILES[@]} file(s) to release $TAG (concurrency: $PARALLEL_JOBS)..."

# 4. Upload files in parallel with per-file retry
FAILED_LOG=$(mktemp)
trap 'rm -f "$FAILED_LOG"' EXIT

upload_file() {
    local file="$1"
    local filename
    filename=$(basename "$file")
    echo "⬆️ $filename..."
    for attempt in 1 2 3; do
        if gh release upload "$TAG" "$file" --clobber -R "$REPO"; then
            echo "✅ $filename"
            return 0
        fi
        echo "::warning::Attempt $attempt/3 failed for $filename, retrying in 5s..."
        sleep 5
    done
    echo "::error::Failed to upload $filename after 3 attempts"
    echo "$filename" >> "$FAILED_LOG"
    return 1
}

job_count=0

for file in "${FILES[@]}"; do
    upload_file "$file" &
    ((job_count++)) || true
    if [ "$job_count" -ge "$PARALLEL_JOBS" ]; then
        wait -n || true
        ((job_count--)) || true
    fi
done
wait

if [ -s "$FAILED_LOG" ]; then
    echo "::error::The following file(s) failed to upload:"
    cat "$FAILED_LOG"
    exit 1
fi

echo "=== All release assets uploaded successfully ==="
