#!/usr/bin/env bash
# Extrait les notes de release ou vide la liste après publication réussie.
set -euo pipefail

file="${RELEASE_NOTES_FILE:-$(dirname "$0")/../RELEASE_NOTES.md}"
marker='<!-- notes -->'

if [[ ! -f "$file" ]] || ! tr -d '\r' < "$file" | grep -qxF "$marker"; then
  echo "Marqueur $marker absent de $file" >&2
  exit 1
fi

case "${1:-}" in
  extract)
    output="${2:?Fichier de sortie manquant}"
    tr -d '\r' < "$file" | awk -v marker="$marker" '
      $0 == marker { seen = 1; next }
      seen && NF {
        while (blank > 0) { print ""; blank-- }
        print
        started = 1
        next
      }
      seen && !NF && started { blank++ }
    ' > "$output"
    ;;
  reset)
    temporary="$(mktemp)"
    tr -d '\r' < "$file" | awk -v marker="$marker" '
      { print }
      $0 == marker { exit }
    ' > "$temporary"
    printf '\n' >> "$temporary"
    mv "$temporary" "$file"
    ;;
  *)
    echo "Usage : $0 extract <fichier> | reset" >&2
    exit 1
    ;;
esac
