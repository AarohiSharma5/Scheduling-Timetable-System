#!/bin/sh
# Container startup: apply DB migrations, then run the main process.
#
# Using a script (instead of a one-line "flask db upgrade && gunicorn ..."
# command) avoids shell-quoting/`&&` issues on some hosts. The worker sets
# RUN_MIGRATIONS=0 so only the web service migrates (avoids a double-run race).
set -e

if [ "${RUN_MIGRATIONS:-1}" != "0" ]; then
  echo "[entrypoint] applying database migrations (flask db upgrade)..."
  flask db upgrade
fi

echo "[entrypoint] starting: $*"
exec "$@"
