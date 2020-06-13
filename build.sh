#!/bin/sh
cd client && yarn install && yarn build && cd ..

docker-compose build web
docker-compose up -d web