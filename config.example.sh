export META_UPSTREAM_DIR=upstream
export META_LAUNCHER_DIR=launcher
export DEPLOY_TO_FOLDER=false
export DEPLOY_FOLDER=/app/public/v1
export DEPLOY_FOLDER_USER=http
export DEPLOY_FOLDER_GROUP=http

export DEPLOY_TO_GIT=true
export GIT_AUTHOR_NAME="Herpington Derpson"
export GIT_AUTHOR_EMAIL="herpderp@derpmail.com"
export GIT_COMMITTER_NAME="$GIT_AUTHOR_NAME"
export GIT_COMMITTER_EMAIL="$GIT_AUTHOR_EMAIL"
export GIT_SSH_COMMAND="ssh -i ${BASEDIR}/config/deploy.key"

export DISCORD_TOKEN="webhook.token"
export DISCORD_ID="webhook.id"
export DISCORD_USER="Meta Error"
