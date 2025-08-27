#!/usr/bin/env sh
set -eu

APP_DIR=${APP_DIR:-/app}
SEL=${APP_FILE:-${PY_APP:-}}

# Detects a script to run (path to a single .py), if specified or uniquely present.
detect_script() {
  if [ -n "${SEL}" ]; then
    case "${SEL}" in
      /*) script_path=${SEL} ;;
      *)  script_path="${APP_DIR}/${SEL}" ;;
    esac
    [ -f "${script_path}" ] && printf '%s\n' "${script_path}" && return 0 || return 1
  fi

  # Look for exactly one top-level Python file.
  # Busybox-friendly counting without arrays.
  files=$(find "${APP_DIR}" -maxdepth 1 -type f -name "*.py" | sort || true)
  count=$(printf '%s\n' "${files}" | sed '/^$/d' | wc -l | tr -d ' ')
  if [ "${count}" -eq 1 ]; then
    printf '%s\n' "${files}"
    return 0
  fi
  return 1
}

# Detects a Python package with __init__.py and runnable __main__.py and prints
# two lines: <cwd> and <module_name> to be used with `python -m`.
detect_module() {
  # Case 1: APP_DIR itself is a package with __main__.py
  if [ -f "${APP_DIR}/__init__.py" ] && [ -f "${APP_DIR}/__main__.py" ]; then
    parent_dir=$(dirname "${APP_DIR}")
    mod_name=$(basename "${APP_DIR}")
    printf '%s\n%s\n' "${parent_dir}" "${mod_name}"
    return 0
  fi

  # Case 2: Exactly one subdirectory is a package with __main__.py
  pkg_dirs=$(find "${APP_DIR}" -mindepth 1 -maxdepth 1 -type d \
              -exec sh -c '[ -f "$1/__init__.py" ] && [ -f "$1/__main__.py" ] && basename "$1"' _ {} \; | sort || true)
  pkg_count=$(printf '%s\n' "${pkg_dirs}" | sed '/^$/d' | wc -l | tr -d ' ')
  if [ "${pkg_count}" -eq 1 ]; then
    mod_name=${pkg_dirs}
    printf '%s\n%s\n' "${APP_DIR}" "${mod_name}"
    return 0
  fi

  return 1
}

# Run a command as a child process, forwarding INT/TERM/HUP to it, and exit with its status.
run_with_traps() {
  # shellcheck disable=SC2039
  child_pid=0

  forward_signal() {
    sig=$1
    if [ ${child_pid} -ne 0 ]; then
      # Try to signal the child; ignore errors to avoid exiting due to `set -e`.
      kill -s "$sig" "${child_pid}" 2>/dev/null || true
    fi
  }

  trap 'forward_signal INT' INT
  trap 'forward_signal TERM' TERM
  trap 'forward_signal HUP' HUP

  # Start the command in a subshell and exec to make the child PID be the Python proc.
  (
    # shellcheck disable=SC2068
    exec "$@"
  ) &
  child_pid=$!

  # Wait for the child and capture exit code.
  wait ${child_pid}
  status=$?

  # Clear traps and exit with child's status.
  trap - INT TERM HUP
  return ${status}
}

# Decide what to run.
ENTRY_SCRIPT=""
ENTRY_CWD=""
ENTRY_MODULE=""

if script_path=$(detect_script); then
  ENTRY_SCRIPT=${script_path}
  [ -r "${ENTRY_SCRIPT}" ] || { echo "Error: App file not readable: ${ENTRY_SCRIPT}" >&2; exit 66; }
  echo "Running script: ${ENTRY_SCRIPT} $*"
  run_with_traps python -u "${ENTRY_SCRIPT}" "$@"
  exit $?
fi

if mod_info=$(detect_module); then
  ENTRY_CWD=$(printf '%s' "${mod_info}" | sed -n '1p')
  ENTRY_MODULE=$(printf '%s' "${mod_info}" | sed -n '2p')
  echo "Running module: ${ENTRY_MODULE} (cwd=${ENTRY_CWD}) $*"
  # Run in a subshell to cd, then exec python -m, while keeping a single child PID.
  run_with_traps sh -c "cd '${ENTRY_CWD}' && exec python -u -m '${ENTRY_MODULE}' \"\$@\"" _ "$@"
  exit $?
fi

# Nothing resolved.
echo "Error: Could not determine how to run app in ${APP_DIR}." >&2
echo "Hints:" >&2
echo "  - Set APP_FILE to a script path relative to APP_DIR, or" >&2
echo "  - Mount a single *.py at top-level, or" >&2
echo "  - Mount a Python package (directory with __init__.py and __main__.py)." >&2

# Provide some diagnostic listing to help users.
echo "Top-level Python files:" >&2
find "${APP_DIR}" -maxdepth 1 -type f -name "*.py" | sort >&2 || true
echo "Candidate package dirs (with __init__ and __main__):" >&2
find "${APP_DIR}" -mindepth 1 -maxdepth 1 -type d \
  -exec sh -c '[ -f "$1/__init__.py" ] && [ -f "$1/__main__.py" ] && printf "%s\n" "$1"' _ {} \; | sort >&2 || true
exit 64
