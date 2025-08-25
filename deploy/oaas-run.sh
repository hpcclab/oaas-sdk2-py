#!/usr/bin/env sh
set -eu

APP_DIR=${APP_DIR:-/app}
SEL=${APP_FILE:-${PY_APP:-}}

resolve_script() {
  if [ -n "${SEL}" ]; then
    case "${SEL}" in
      /*) printf "%s\n" "${SEL}" ;;
      *)  printf "%s/%s\n" "${APP_DIR}" "${SEL}" ;;
    esac
  else
    files=$(find "${APP_DIR}" -maxdepth 1 -type f -name "*.py" | sort)
    count=$(printf "%s\n" "${files}" | sed '/^$/d' | wc -l | tr -d ' ')
    if [ "${count}" -eq 1 ]; then
      printf "%s\n" "${files}"
    else
      echo "Error: Could not uniquely determine app file in ${APP_DIR}." >&2
      echo "Hint: set APP_FILE env or mount exactly one *.py file." >&2
      if [ "${count}" -gt 0 ]; then
        echo "Found ${count} files:" >&2
        printf "%s\n" "${files}" >&2
      fi
      exit 64
    fi
  fi
}

SCRIPT=$(resolve_script)
[ -r "${SCRIPT}" ] || { echo "Error: App file not readable: ${SCRIPT}" >&2; exit 66; }

echo "Running: ${SCRIPT} $*"
exec python -u "${SCRIPT}" "$@"
