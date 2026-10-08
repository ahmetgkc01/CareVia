# Carevia operations runbook

## Deployment checks

Before every deployment:

1. Run backend lint, tests, migration drift detection, and frontend lint, tests, and build.
2. Back up the database and record the backup identifier.
3. Run `python manage.py migrate --plan` before applying migrations.
4. Deploy containers, then confirm `/api/health/` returns HTTP 200.
5. Test login with one staff account and one patient account.
6. Confirm that application logs are valid single-line JSON and contain no request bodies.

Set `CAREVIA_RELEASE` to the deployed Git commit SHA when starting the production containers. The
health response exposes this non-secret value so operators can distinguish a healthy old release
from the intended deployment:

```bash
CAREVIA_RELEASE="$(git rev-parse HEAD)" docker compose -f deploy/compose.prod.yaml up -d
python deploy/check_health.py "https://carevia.example.com" \
  --expected-release "$(git rev-parse HEAD)"
```

Configure the `CAREVIA_PRODUCTION_URL` GitHub repository variable to enable the hourly
`Production health` workflow. After a deployment, run that workflow manually with the deployed SHA;
the `production` environment then records the verification result and public URL.

Set `CAREVIA_DOMAIN` to the public hostname before loading `deploy/Caddyfile.lightsail` into Caddy.
The Caddy process must receive this environment variable; the file defaults to `carevia.localhost` so
an omitted production hostname cannot accidentally claim an unrelated public domain.

## PostgreSQL backup

RDS automated backups remain the primary recovery mechanism. Before a risky migration, also take
a manual RDS snapshot. For a portable logical backup, run from a trusted host with the runtime
database credentials supplied through environment variables:

```bash
pg_dump --format=custom --no-owner --no-acl --file=carevia.dump "$DATABASE_URL"
```

Never commit a dump. It may contain sensitive data even when the current demo dataset is synthetic.

## Restore drill

Restore into a separate database, never over the active database:

```bash
createdb "$RESTORE_DATABASE_NAME"
pg_restore --exit-on-error --no-owner --no-acl --dbname="$RESTORE_DATABASE_URL" carevia.dump
```

After restoring, run Django's deployment check and call `/api/health/`. Verify row counts for users,
patients, clinicians, appointments, and audit events. Perform a restore drill after material schema
changes and at least quarterly for a long-running environment.

## Monitoring

Monitor the public health endpoint from outside AWS and alert on repeated non-200 responses. In AWS,
alert on RDS CPU, free storage, free memory, and connection saturation. Route alerts to a confirmed
team address. Do not include patient fields, chat content, credentials, or request bodies in alerts.

## Demo reset

Use a disposable database for public demos. Recreate it with migrations, `seed_roles`, `seed_demo`,
and `seed_knowledge`; do not delete or reseed a shared environment in place. Keep production and demo
credentials separate.
