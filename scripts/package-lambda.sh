#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
output_zip="${1:-${project_root}/dist/paper2proof-lambda.zip}"
staging_root="$(mktemp -d)"
trap 'rm -rf "${staging_root}"' EXIT

mkdir -p "$(dirname "${output_zip}")" "${staging_root}/package"
requirements_lock="${project_root}/services/api/requirements.lock.txt"
if [[ ! -f "${requirements_lock}" ]]; then
  echo "missing compiled Lambda requirements: ${requirements_lock}" >&2
  exit 1
fi
"${project_root}/.venv/bin/python" -m pip install \
  --requirement "${requirements_lock}" \
  --require-hashes \
  --quiet \
  --no-compile \
  --target "${staging_root}/package" \
  --platform manylinux2014_aarch64 \
  --implementation cp \
  --python-version 3.13 \
  --only-binary=:all:

mkdir -p "${staging_root}/package/paper2proof"
for module in __init__.py agentcore_client.py api.py config.py fixtures.py queue.py rate_limit.py reporting.py schemas.py; do
  cp "${project_root}/services/agent/src/paper2proof/${module}" \
    "${staging_root}/package/paper2proof/${module}"
done
cp -R "${project_root}/services/agent/src/paper2proof/web" \
  "${staging_root}/package/paper2proof/web"
cp -R "${project_root}/fixtures" "${staging_root}/package/fixtures"
cp "${project_root}/services/api/handler.py" "${staging_root}/package/handler.py"
cp "${project_root}/services/api/worker.py" "${staging_root}/package/worker.py"

rm -f "${output_zip}"
find "${staging_root}/package" -exec touch -h -t 202001010000 {} +
(
  cd "${staging_root}/package"
  find . -type f | LC_ALL=C sort | zip -q -X "${output_zip}" -@
)
echo "${output_zip}"
