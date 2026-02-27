# GeoNode GIS Installation Notes
> MacOS Apple Silicon (ARM64/M-series) — Docker Compose setup
> GeoNode version: `master` | GeoServer: `2.27.4` | PostGIS: `15-3.5`

---

## Prerequisites

| Tool | Required | Check |
|------|----------|-------|
| Docker Desktop | ✅ | `docker --version` |
| Docker Compose v2 | ✅ | `docker compose version` |
| Python 3 | ✅ | `python3 --version` |
| Git | ✅ | `git --version` |

---

## Step 1 — Clone the geonode-project template

```bash
git clone https://github.com/GeoNode/geonode-project.git geonode
cd geonode
```

---

## Step 2 — Generate the `.env` file

Use the included helper script. Pass `--noinput` to skip the interactive prompt.

```bash
python3 create-envfile.py --noinput --hostname localhost --env_type dev
```

This generates `.env` with random secure passwords for all services.

---

## Step 3 — Change HTTP port (if port 80 is in use)

Edit `.env` — find and update:

```env
HTTP_PORT=8888          # change from 80 to any free port
SITEURL=http://localhost:8888/
```

---

## ⚠️ MISTAKE 1 — Apple Silicon platform mismatch

**Problem:** `docker compose build` fails with:
```
no match for platform in manifest: not found
target db: failed to solve: geonode/postgis:15-3.5-latest
```

**Cause:** `geonode/postgis` only ships `linux/amd64` — no `linux/arm64` image exists.

**Fix:** Add this line to `.env` and always prefix `docker compose` commands with the env var:

```env
# .env
DOCKER_DEFAULT_PLATFORM=linux/amd64
```

Then build with:
```bash
DOCKER_DEFAULT_PLATFORM=linux/amd64 docker compose build
```

This forces Docker Desktop to use **Rosetta 2 emulation** for amd64 images on Apple Silicon.

---

## Step 4 — Build Docker images

```bash
DOCKER_DEFAULT_PLATFORM=linux/amd64 docker compose build
```

**Expected duration:** 10–20 minutes on first run (pulls ~2 GB of images, installs Python deps, clones MapStore client).

**Slowest steps:**
- `#50` — cloning `geonode-mapstore-client` submodules (~3–5 min)
- `#53` — final `pip install -e .` which re-clones GeoNode core (~3–5 min)

All 6 images built successfully when you see:
```
 geoserver  Built
 letsencrypt  Built
 geonode  Built
 data-dir-conf  Built
 db  Built
 django  Built
```

---

## Step 5 — Start all containers

```bash
DOCKER_DEFAULT_PLATFORM=linux/amd64 docker compose up -d
```

---

## ⚠️ MISTAKE 2 — GeoServer port 8080 already allocated

**Problem:** GeoServer fails to start:
```
Bind for 0.0.0.0:8080 failed: port is already allocated
```

**Cause:** Another Docker container (e.g. a previous GeoNode install or Jenkins) was already using port 8080.

**Fix:** Change GeoServer's external port in `docker-compose.yml`:

```yaml
# docker-compose.yml — geoserver service
ports:
  - "8090:8080"    # changed from 8080:8080
```

Also update `.env`:
```env
GEOSERVER_LB_PORT=8090
```

Then recreate the GeoServer container:
```bash
DOCKER_DEFAULT_PLATFORM=linux/amd64 docker compose up -d geoserver
```

---

## ⚠️ MISTAKE 3 — Docker Desktop socket unresponsive

**Problem:** All `docker` CLI commands hang indefinitely (no output, no timeout).

**Cause:** Docker Desktop was in a broken/stale state — processes were running but the daemon socket was unresponsive.

**Diagnosis:**
```bash
curl -s --max-time 5 --unix-socket ~/.docker/run/docker.sock http://localhost/_ping
# Returns exit code 28 (timeout) instead of "OK"
```

**Fix:** Force-restart Docker Desktop:
```bash
# Quit via AppleScript
osascript -e 'quit app "Docker Desktop"'

# If still running after a few seconds, force kill
pkill -9 -f "com.docker"

# Relaunch
open -a "Docker Desktop"

# Wait for it to be ready (up to 2 min)
until curl -s --max-time 3 --unix-socket ~/.docker/run/docker.sock http://localhost/_ping | grep -q OK; do
  sleep 5; echo "Still starting..."
done
echo "Docker ready!"
```

---

## Final Container Status

```bash
DOCKER_DEFAULT_PLATFORM=linux/amd64 docker compose ps
```

| Container | Image | Status |
|-----------|-------|--------|
| `django4geonode_project` | geonode:master | ✅ healthy |
| `celery4geonode_project` | geonode:master | ✅ running |
| `db4geonode_project` | postgis:15-3.5 | ✅ healthy |
| `geoserver4geonode_project` | geoserver:2.27.4 | ✅ healthy |
| `gsconf4geonode_project` | geoserver_data | ✅ healthy |
| `nginx4geonode_project` | nginx:1.28.0 | ✅ running |
| `redis4geonode_project` | redis:7-alpine | ✅ running |
| `memcached4geonode_project` | memcached:alpine | ✅ healthy |
| `letsencrypt4geonode_project` | letsencrypt | ⚠️ restarting (normal in HTTP/dev mode) |

> `letsencrypt` restarting is **expected** — it only works with a real domain + HTTPS.

---

## Access

| Service | URL |
|---------|-----|
| GeoNode web UI | http://localhost:8888/ |
| GeoServer admin | http://localhost:8090/geoserver/ |

### Admin credentials (auto-generated in `.env`)

```bash
# GeoNode
grep "^ADMIN_USERNAME\|^ADMIN_PASSWORD" .env

# GeoServer
grep "^GEOSERVER_ADMIN" .env
```

---

## Common Commands

```bash
# View running containers
DOCKER_DEFAULT_PLATFORM=linux/amd64 docker compose ps

# Follow Django logs
DOCKER_DEFAULT_PLATFORM=linux/amd64 docker compose logs -f django

# Follow GeoServer logs
DOCKER_DEFAULT_PLATFORM=linux/amd64 docker compose logs -f geoserver

# Stop all containers (keeps data volumes)
DOCKER_DEFAULT_PLATFORM=linux/amd64 docker compose down

# Stop and delete ALL data (full reset)
DOCKER_DEFAULT_PLATFORM=linux/amd64 docker compose down -v

# Restart a single service
DOCKER_DEFAULT_PLATFORM=linux/amd64 docker compose restart django

# Start from scratch after a full reset
DOCKER_DEFAULT_PLATFORM=linux/amd64 docker compose up -d
```

---

## Tips

- Always prefix commands with `DOCKER_DEFAULT_PLATFORM=linux/amd64` on Apple Silicon.
- Or export it once per terminal session: `export DOCKER_DEFAULT_PLATFORM=linux/amd64`
- The `.env` file contains all passwords — keep it out of version control (already in `.gitignore`).
- First startup of Django takes ~60s for DB migrations and static file collection.
- GeoServer takes ~2–3 min to become healthy after starting.
