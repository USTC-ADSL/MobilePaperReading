#!/bin/sh
set -eu

deploy_root=/srv/paper-kb
source_dir="$deploy_root/source"
site_dir="$deploy_root/site"
deploy_key="$deploy_root/github-deploy-key"

export GIT_SSH_COMMAND="ssh -i $deploy_key -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=$deploy_root/github-known-hosts"

git -C "$source_dir" fetch --prune origin main
current=$(git -C "$source_dir" rev-parse HEAD)
target=$(git -C "$source_dir" rev-parse origin/main)

if [ "$current" = "$target" ]; then
    exit 0
fi

git -C "$source_dir" reset --hard origin/main
"$deploy_root/venv/bin/mkdocs" build \
    --clean \
    --config-file "$source_dir/mkdocs.yml" \
    --site-dir "$site_dir"

docker compose \
    -f "$source_dir/deploy/oauth/docker-compose.yml" \
    up -d --build --remove-orphans
