#!/usr/bin/env bash
set -euo pipefail

if ! command -v terraform >/dev/null 2>&1; then
  echo "error: terraform is not installed or not available in PATH"
  exit 1
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
all_terraform_dirs=(
  "terraform"
  "terraform/modules/vpc"
  "terraform/modules/iam"
  "terraform/modules/cluster"
)

init_timeout_seconds="${TERRAFORM_INIT_TIMEOUT_SECONDS:-180}"
validate_timeout_seconds="${TERRAFORM_VALIDATE_TIMEOUT_SECONDS:-90}"
plugin_cache_dir="${TERRAFORM_PLUGIN_CACHE_DIR:-${repo_root}/.terraform-plugin-cache}"
validate_scope="${TERRAFORM_VALIDATE_SCOPE:-changed}"

mkdir -p "${plugin_cache_dir}"
export TF_PLUGIN_CACHE_DIR="${plugin_cache_dir}"

select_validate_dir_from_file() {
  local file="$1"

  case "${file}" in
    terraform/modules/vpc/*)
      echo "terraform/modules/vpc"
      ;;
    terraform/modules/iam/*)
      echo "terraform/modules/iam"
      ;;
    terraform/modules/cluster/*)
      echo "terraform/modules/cluster"
      ;;
    terraform/*)
      echo "terraform"
      ;;
  esac
}

compute_changed_dirs() {
  local file
  declare -A dirs_map=()

  while IFS= read -r file; do
    [ -n "${file}" ] || continue
    selected_dir="$(select_validate_dir_from_file "${file}")"
    [ -n "${selected_dir}" ] && dirs_map["${selected_dir}"]=1
  done < <(git -C "${repo_root}" diff --name-only -- terraform)

  while IFS= read -r file; do
    [ -n "${file}" ] || continue
    selected_dir="$(select_validate_dir_from_file "${file}")"
    [ -n "${selected_dir}" ] && dirs_map["${selected_dir}"]=1
  done < <(git -C "${repo_root}" diff --name-only --cached -- terraform)

  while IFS= read -r file; do
    [ -n "${file}" ] || continue
    selected_dir="$(select_validate_dir_from_file "${file}")"
    [ -n "${selected_dir}" ] && dirs_map["${selected_dir}"]=1
  done < <(git -C "${repo_root}" ls-files --others --exclude-standard -- terraform)

  if git -C "${repo_root}" rev-parse --verify "@{upstream}" >/dev/null 2>&1; then
    local base_ref
    base_ref="$(git -C "${repo_root}" merge-base HEAD "@{upstream}")"
    while IFS= read -r file; do
      [ -n "${file}" ] || continue
      selected_dir="$(select_validate_dir_from_file "${file}")"
      [ -n "${selected_dir}" ] && dirs_map["${selected_dir}"]=1
    done < <(git -C "${repo_root}" diff --name-only "${base_ref}"...HEAD -- terraform)
  fi

  for dir in "${all_terraform_dirs[@]}"; do
    if [ -n "${dirs_map[${dir}]+x}" ]; then
      echo "${dir}"
    fi
  done
}

run_with_timeout() {
  local timeout_seconds="$1"
  shift

  if command -v timeout >/dev/null 2>&1; then
    local status=0
    timeout "${timeout_seconds}" "$@" || status=$?
    if [ "${status}" -eq 124 ]; then
      echo "error: command timed out after ${timeout_seconds}s: $*"
    fi
    return "${status}"
  fi

  "$@"
}

validate_dir() {
  local dir="$1"
  local abs_dir="${repo_root}/${dir}"
  local validate_output_file
  validate_output_file="$(mktemp)"

  if run_with_timeout "${validate_timeout_seconds}" terraform -chdir="${abs_dir}" validate -no-color >"${validate_output_file}" 2>&1; then
    echo "info: terraform validate (${dir})"
    rm -f "${validate_output_file}"
    return 0
  fi

  if grep -Eiq "terraform init|initialized|initialise|initialize|there is no package for|cached in \.terraform/providers" "${validate_output_file}"; then
    echo "info: terraform init (${dir})"
    run_with_timeout "${init_timeout_seconds}" terraform -chdir="${abs_dir}" init -backend=false -input=false -lockfile=readonly -no-color -upgrade=false >/dev/null
    echo "info: terraform validate (${dir})"
    run_with_timeout "${validate_timeout_seconds}" terraform -chdir="${abs_dir}" validate -no-color >/dev/null
    rm -f "${validate_output_file}"
    return 0
  fi

  echo "error: terraform validate failed (${dir})"
  cat "${validate_output_file}"
  rm -f "${validate_output_file}"
  return 1
}

terraform_dirs=()
if [ "${validate_scope}" = "all" ]; then
  terraform_dirs=("${all_terraform_dirs[@]}")
else
  while IFS= read -r dir; do
    [ -n "${dir}" ] && terraform_dirs+=("${dir}")
  done < <(compute_changed_dirs)
fi

if [ "${#terraform_dirs[@]}" -eq 0 ]; then
  echo "info: terraform validate skipped (no terraform changes detected)"
  exit 0
fi

pids=()
for dir in "${terraform_dirs[@]}"; do
  validate_dir "${dir}" &
  pids+=("$!")
done

status=0
for pid in "${pids[@]}"; do
  if ! wait "${pid}"; then
    status=1
  fi
done

if [ "${status}" -ne 0 ]; then
  exit "${status}"
fi

echo "info: terraform validate passed for root and modules"
