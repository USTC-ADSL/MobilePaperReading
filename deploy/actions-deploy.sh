#!/bin/sh
set -eu

deploy_root=/srv/paper-kb
source_dir="$deploy_root/source"
site_dir="$deploy_root/site"
mkdocs="$deploy_root/venv/bin/mkdocs"

"$mkdocs" build \
    --clean \
    --config-file "$source_dir/mkdocs.yml" \
    --site-dir "$site_dir"

mkdir -p "$site_dir/admin"
cp "$source_dir/admin/index.html" "$site_dir/admin/index.html"
cp "$source_dir/admin/config.yml" "$site_dir/admin/config.yml"

oauth_env=/data/services/paper-kb/oauth.env
if [ -f "$oauth_env" ]; then
    docker compose \
        -f "$source_dir/deploy/oauth/docker-compose.yml" \
        up -d --build --remove-orphans
else
    printf '%s\n' 'OAuth env is not configured; skipped OAuth service.' >&2
fi

