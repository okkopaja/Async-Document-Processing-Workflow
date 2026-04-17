#!/usr/bin/env bash
docker compose -f infra/compose/docker-compose.dev.yml --env-file .env.example down -v
docker compose -f infra/compose/docker-compose.dev.yml --env-file .env.example up --build
