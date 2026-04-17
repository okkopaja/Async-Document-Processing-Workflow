# Production Deployment (Single EC2)

This stack is configured for `project.hiderview.app` and runs behind Caddy with automatic HTTPS.

## 1. Prepare environment file

From repo root:

```bash
cp infra/compose/env.prod.example .env.prod
```

Edit `.env.prod` and set strong secrets at minimum:

- `POSTGRES_PASSWORD`
- `DATABASE_URL` password (must match Postgres password)

## 2. DNS and Security Group

- Point `project.hiderview.app` A record to your EC2 public IP.
- Open inbound TCP `80` and `443` to the instance.
- Keep `22` restricted to your own IP.

## 3. Start services

From repo root:

```bash
chmod +x infra/scripts/preflight-prod.sh
infra/scripts/preflight-prod.sh
docker compose -f infra/compose/docker-compose.prod.yml --env-file .env.prod up -d --build
```

Optional full gate with image build check:

```bash
infra/scripts/preflight-prod.sh infra/compose/docker-compose.prod.yml .env.prod --build-check
```

## 4. Verify

```bash
docker compose -f infra/compose/docker-compose.prod.yml --env-file .env.prod ps
docker compose -f infra/compose/docker-compose.prod.yml --env-file .env.prod logs -f caddy api worker web
```

Health endpoint:

```bash
curl -I https://project.hiderview.app/api/health
```

## 5. Operations

Stop:

```bash
docker compose -f infra/compose/docker-compose.prod.yml --env-file .env.prod down
```

Restart with rebuild:

```bash
docker compose -f infra/compose/docker-compose.prod.yml --env-file .env.prod up -d --build
```

## Notes

- Only Caddy is exposed publicly (`80/443`).
- Postgres and Redis are internal-only services in this compose file.
- API and worker share `uploads_data` so background parsing can read uploaded files.