# Running BuildOS AI in production

Everything here uses `deploy/docker-compose.prod.yml`. Commands are run from the repo root.
`$COMPOSE` below means:

```bash
COMPOSE="docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env.production"
```

## Still to decide before a real launch

These need choices that haven't been made yet, so they are not set up:

- **Domain and TLS (BUILD-139).** The stack publishes the frontend on port 3000 and the API on 8000 over plain HTTP. Put a TLS-terminating reverse proxy (Caddy, nginx, or a cloud load balancer) in front, and set `FORWARDED_ALLOW_IPS` to its address so login rate limits see real client IPs.
- **Database hosting (BUILD-136).** The stack runs Postgres in a container with a Docker volume. A managed Postgres (RDS, Cloud SQL, etc.) would give you automatic backups and failover. To use one, drop the `db` service and point `DATABASE_URL` at it.
- **File storage (BUILD-138).** Uploads go to the `uploads` Docker volume, which is local disk. Moving to S3-compatible storage means replacing `app/core/storage.py` (callers only use opaque keys).

## First deploy

1. `cp deploy/.env.production.example deploy/.env.production` and fill it in. The backend **refuses to start** in production with the default JWT secret, the example database password, or localhost CORS origins.
2. `$COMPOSE up -d --build`
3. Check: `curl http://localhost:8000/api/v1/health/ready` should return `{"status":"ok","database":"ok"}`.

The backend runs `alembic upgrade head` every time it starts, so the database schema is created on first start and updated on every deploy.

## Updating

```bash
git pull
$COMPOSE up -d --build
```

Take a backup first (below). Migrations run automatically when the new backend container starts. If one fails, the container exits and the old schema is untouched (Postgres DDL is transactional).

## Health and logs

- `GET /api/v1/health` is liveness: the process is up.
- `GET /api/v1/health/ready` is readiness: it can reach the database. Returns 503 if not. The backend container's Docker healthcheck uses it.
- `$COMPOSE logs -f backend` shows one line per request:
  `request_id=... method=GET path=/api/v1/projects status=200 duration_ms=12.3`
  Every response carries the same ID in its `X-Request-ID` header, so a user's error can be matched to its log line. Query strings are never logged. Set `LOG_LEVEL=DEBUG` for more detail.

## Backups

`deploy/backup.sh` writes two files to `./backups` (or `BACKUP_DIR`):

- `buildos-db-<time>.dump`, the database (`pg_dump` custom format)
- `buildos-files-<time>.tar.gz`, uploaded documents and photos

It checks each file is readable before keeping it, and deletes backups older than `KEEP_DAYS` (default 14). Schedule it daily and **copy the backups off the server**. Example cron:

```
0 2 * * * cd /srv/buildos && deploy/backup.sh >> /var/log/buildos-backup.log 2>&1
```

## Restoring

Restore into a running stack (this **replaces** the current data):

```bash
$COMPOSE stop backend frontend
$COMPOSE exec -T db sh -c 'pg_restore --clean --if-exists --no-owner -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < backups/buildos-db-<time>.dump
$COMPOSE run --rm -T --no-deps --entrypoint sh backend -c 'rm -rf /app/storage_data/* && tar -xzf - -C /app/storage_data' < backups/buildos-files-<time>.tar.gz
$COMPOSE start backend frontend
```

Practise this on a spare machine before you need it.

## Scaling limits to know about

- **One backend worker/container.** Login rate limits are counted in process memory (`app/core/rate_limit.py`). More workers or containers would each keep their own count; move the limiter to Redis (already in the stack) first.
- **Migrations on start** assume a single backend container. With several, run `alembic upgrade head` as a separate one-off step instead.
