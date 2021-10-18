#!/bin/bash

set -e

docker build -t simone:latest .
docker rm simone-old || true
docker rename simone simone-old
docker stop simone-old

. .env

docker run -d --restart=unless-stopped --name simone -e ENV=prod -e DJANGO_SECRET_KEY -e SLACK_BOT_TOKEN -e SLACK_SIGNING_SECRET -e SIMONE_DB_NAME -e SIMONE_DB_USER -e SIMONE_DB_PASSWORD -e SIMONE_DB_HOST -p 6444:6444 simone:latest
