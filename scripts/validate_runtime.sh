#!/usr/bin/env bash

set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${ROOT_DIR}/.universal_mcp_runtime/validation"
TIMESTAMP="$(date +"%Y%m%d_%H%M%S")"
RUN_DIR="${LOG_DIR}/${TIMESTAMP}"

mkdir -p "${RUN_DIR}"

STARTED_DAEMON=0
FAILURES=0

cleanup() {
  if [[ "${STARTED_DAEMON}" -eq 1 ]]; then
    (
      cd "${ROOT_DIR}" &&
        umcp stop
    ) >"$(step_log_path "stop")" 2>&1 || true
  fi
}

trap cleanup EXIT

step_log_path() {
  local step_name="$1"
  printf "%s/%s.log" "${RUN_DIR}" "${step_name}"
}

run_step() {
  local step_name="$1"
  shift

  local log_file
  log_file="$(step_log_path "${step_name}")"

  printf "\n==> %s\n" "${step_name}"
  printf "Command: %s\n" "$*"

  (
    cd "${ROOT_DIR}" &&
      "$@"
  ) >"${log_file}" 2>&1
  local exit_code=$?

  if [[ ${exit_code} -eq 0 ]]; then
    printf "Result: OK\n"
  else
    printf "Result: FAIL (%s)\n" "${exit_code}"
    FAILURES=$((FAILURES + 1))
  fi

  printf "Log: %s\n" "${log_file}"
  sed -n '1,120p' "${log_file}"
  return "${exit_code}"
}

printf "Universal MCP runtime validation\n"
printf "Root: %s\n" "${ROOT_DIR}"
printf "Run dir: %s\n" "${RUN_DIR}"

run_step "doctor" umcp doctor || true
run_step "probe_daemon" umcp probe-daemon || true

if run_step "start" umcp start; then
  STARTED_DAEMON=1
  run_step "status" umcp status || true
  run_step "run_dry_codex_version" umcp run --dry-run codex -- --version || true
  run_step "run_codex_version" umcp run codex -- --version || true
else
  printf "\nDaemon start failed. Skipping status and codex runtime launch steps.\n"
fi

printf "\nSummary\n"
if [[ "${FAILURES}" -eq 0 ]]; then
  printf "Validation completed without failures.\n"
else
  printf "Validation completed with %s failing step(s).\n" "${FAILURES}"
fi
printf "Detailed logs: %s\n" "${RUN_DIR}"

if [[ "${FAILURES}" -ne 0 ]]; then
  exit 1
fi
