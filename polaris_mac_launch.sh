#!/bin/bash
# AI-context: macOS double-click launcher with self-heal. Subcommands: doctor, nuke, watch. file_mtime() is OS-aware (BSD vs GNU stat). docker_compose_up_with_heal auto-wipes volume on stale-password detection. See DEVNOTES/known-gotchas.md.
# =============================================================================
#  POLARIS / macOS Launch Controller
#  Version: 2.5  /  2026-05-08
#
#  Single entry point for everything: bring-up, tear-down, logs, tests, reset.
#  Auto-routes to Docker (preferred) or native Homebrew + venv.
#
#  USAGE
#      ./polaris_mac_launch.sh                  Detect runtime, launch + watch
#      ./polaris_mac_launch.sh up               Same as default
#      ./polaris_mac_launch.sh up --detach      Launch in background, return
#      ./polaris_mac_launch.sh rebuild          Force clean Docker rebuild + watch
#      ./polaris_mac_launch.sh nuke             Total wipe (containers, image,
#                                               volume, state) — destructive
#      ./polaris_mac_launch.sh stop             Graceful shutdown
#      ./polaris_mac_launch.sh status           What is running, where
#      ./polaris_mac_launch.sh doctor           Read-only diagnostic (does
#                                               not modify anything)
#      ./polaris_mac_launch.sh logs [svc]       Tail logs (default: app)
#      ./polaris_mac_launch.sh test             Run full test suite
#      ./polaris_mac_launch.sh reset            Drop pgdata, keep image
#      ./polaris_mac_launch.sh --port 5050      Override host port
#      ./polaris_mac_launch.sh --native         Force native path
#      ./polaris_mac_launch.sh --docker         Force Docker path
#      ./polaris_mac_launch.sh --help           This help
#
#  SELF-HEALING
#      If the app comes up but cannot authenticate against the database
#      (typically: stale Postgres data volume from an earlier session with
#      different credentials), the launcher detects this in the db logs,
#      drops the volume automatically, and rebrings the stack up. You will
#      see "Detected stale-volume auth failure" in the launcher output if
#      this happens.
#
#  TOTALLY BROKEN STATE
#      If something is so wrong that even rebuild can't fix it, run:
#          ./polaris_mac_launch.sh nuke
#      Then:
#          ./polaris_mac_launch.sh up
#
#  WATCH MODE (default for `up` and `rebuild`)
#      After bringing the stack up, the script stays in the foreground
#      watching for the browser. The page sends a heartbeat every 10s while
#      the tab is open, and a quit beacon when you close it. The launcher
#      tears the stack down automatically when:
#        - You close the Polaris browser tab/window
#        - You press Ctrl+C in this terminal
#        - The heartbeat goes stale for >45 seconds (browser crash / network)
#      Pass --detach to skip the watcher and run in the background as before.
#
#  DOUBLE-CLICK LAUNCH (no terminal commands)
#      Double-click `Polaris.command` in Finder. macOS opens it with Terminal,
#      brings the stack up, opens the browser, and stays alive watching. The
#      Terminal window stays open so you can see status; close it (or close
#      the browser tab) to shut everything down.
#
#  PORTABILITY
#      All paths are resolved relative to this script via $BASH_SOURCE, so
#      the polaris/ folder can sit anywhere (Desktop, Documents, Downloads).
#      The script cd's to its own folder at startup as belt-and-suspenders.
#
#  PREREQS
#      Docker Desktop (recommended) OR Homebrew. Mac with Bash 3+.
# =============================================================================

set -eu
# Strict mode + error visibility:
# - set -e: any unchecked command failure terminates the script.
# - set -u: unset variables are an error.
# - The traps below ensure that BEFORE the script exits, the user sees
#   exactly which line and which command failed, and that the Terminal
#   window stays open so the message is actually readable.

# -----------------------------------------------------------------------------
# Robustness traps: keep Terminal open on error AND on Finder double-click,
# so users can actually read the output before the window vanishes.
# -----------------------------------------------------------------------------
_PAUSE_ON_EXIT=0
_LAST_LINE=0
_LAST_CMD="(none)"

# Detect "launched by double-click from Finder" vs "invoked from a shell".
# Finder-launched scripts have parent process == "login" (or "Terminal").
_detect_finder_launch() {
    local pcmd
    pcmd="$(ps -p $PPID -o comm= 2>/dev/null | tr -d ' ' || true)"
    case "$pcmd" in
        login|Terminal|iTerm2|*Terminal*) _PAUSE_ON_EXIT=1 ;;
        *) _PAUSE_ON_EXIT=0 ;;
    esac
    case "${POLARIS_PAUSE:-}" in
        1) _PAUSE_ON_EXIT=1 ;;
        0) _PAUSE_ON_EXIT=0 ;;
    esac
}

_track() { _LAST_LINE="$1"; _LAST_CMD="$2"; }

_on_error() {
    local code=$?
    printf "\n\033[0;31m[x] FAILED\033[0m at line %s\n" "$_LAST_LINE" >&2
    printf "    Command: %s\n"   "$_LAST_CMD"  >&2
    printf "    Exit code: %s\n" "$code"       >&2
    # EXIT trap will run after this and pause if Finder-launched.
}

_on_exit() {
    if (( _PAUSE_ON_EXIT == 1 )); then
        printf "\n\033[2mPress Return to close this window...\033[0m"
        # Read from /dev/tty so this works even with redirected stdin.
        read -r _ < /dev/tty 2>/dev/null || true
    fi
}

trap '_track "$LINENO" "$BASH_COMMAND"' DEBUG
trap _on_error ERR
trap _on_exit EXIT

_detect_finder_launch

fatal() {
    printf "\033[0;31m[x]\033[0m %s\n" "$1" >&2
    exit "${2:-1}"
}

# -----------------------------------------------------------------------------
# Paths and constants
# -----------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POLARIS_ROOT="$SCRIPT_DIR"
WEB_DIR="$POLARIS_ROOT/polaris_web"
SQL_DIR="$POLARIS_ROOT/polaris_sql"
CLI_DIR="$POLARIS_ROOT/polaris_cli"

# Anchor working directory to the script's folder. Every path the script
# touches is derived from $SCRIPT_DIR, so the script works no matter where
# you place the polaris/ folder (Desktop, Documents, anywhere else).
cd "$SCRIPT_DIR" || { echo "[x] Cannot cd to $SCRIPT_DIR" >&2; exit 1; }

PID_FILE="/tmp/polaris_app.pid"
LOG_FILE="/tmp/polaris_app.log"
DEFAULT_PORT=2222
PORT="${POLARIS_PORT:-$DEFAULT_PORT}"
HEALTH_TIMEOUT=60   # seconds

# -----------------------------------------------------------------------------
# Colors
# -----------------------------------------------------------------------------
if [[ -t 1 ]]; then
    RED=$'\033[0;31m'; GREEN=$'\033[0;32m'; YELLOW=$'\033[1;33m'
    BLUE=$'\033[0;34m'; MAGENTA=$'\033[0;35m'; CYAN=$'\033[0;36m'
    BOLD=$'\033[1m'; DIM=$'\033[2m'; NC=$'\033[0m'
else
    RED=''; GREEN=''; YELLOW=''; BLUE=''; MAGENTA=''; CYAN=''; BOLD=''; DIM=''; NC=''
fi

log()     { printf "%s>%s %s\n" "$CYAN"   "$NC" "$1"; }
ok()      { printf "%s[ok]%s %s\n" "$GREEN" "$NC" "$1"; }
warn()    { printf "%s[!]%s %s\n"  "$YELLOW" "$NC" "$1"; }
err()     { printf "%s[x]%s %s\n"  "$RED"  "$NC" "$1" >&2; }

banner() {
    printf "\n%s%s================================================================%s\n" "$BOLD" "$MAGENTA" "$NC"
    printf "%s%s  POLARIS Identity Token System  /  macOS Launch Controller    %s\n" "$BOLD" "$MAGENTA" "$NC"
    printf "%s%s================================================================%s\n\n" "$BOLD" "$MAGENTA" "$NC"
}

# -----------------------------------------------------------------------------
# Sanity: required directories present
# -----------------------------------------------------------------------------
require_layout() {
    for d in "$WEB_DIR" "$SQL_DIR" "$CLI_DIR"; do
        if [[ ! -d "$d" ]]; then
            err "Missing required directory: $d"
            err "Place this script at the polaris/ root next to polaris_web/, polaris_sql/, polaris_cli/."
            exit 1
        fi
    done

    # Defense in depth: zip extraction can drop the +x bit on shell scripts,
    # which then fails inside the Postgres init phase with exit code 126.
    # Restore the bit on the scripts that need it before any container starts.
    [[ -f "$WEB_DIR/docker-init.sh"        ]] && chmod +x "$WEB_DIR/docker-init.sh"        2>/dev/null || true
    [[ -f "$WEB_DIR/setup.sh"              ]] && chmod +x "$WEB_DIR/setup.sh"              2>/dev/null || true
    [[ -f "$SCRIPT_DIR/Polaris.command"    ]] && chmod +x "$SCRIPT_DIR/Polaris.command"    2>/dev/null || true
}

# -----------------------------------------------------------------------------
# Port preflight: detect macOS AirPlay Receiver on :5000 and other conflicts
# -----------------------------------------------------------------------------
port_in_use() {
    lsof -nP -iTCP:"$1" -sTCP:LISTEN 2>/dev/null | grep -q LISTEN
}

port_owner() {
    lsof -nP -iTCP:"$1" -sTCP:LISTEN 2>/dev/null | awk 'NR==2 {print $1, $2}'
}

preflight_port() {
    if ! command -v lsof >/dev/null 2>&1; then
        return 0
    fi
    if ! port_in_use "$PORT"; then
        return 0
    fi
    local owner
    owner="$(port_owner "$PORT")"
    # If the listener is our own Docker proxy or gunicorn, that's fine; the
    # idempotent up paths will detect "already running" downstream.
    if echo "$owner" | grep -qiE 'docker|com.docke|gunicorn|python'; then
        return 0
    fi
    err "Port $PORT is held by: $owner"
    if [[ "$PORT" == "5000" ]] && echo "$owner" | grep -qi 'controlce'; then
        echo
        warn "macOS AirPlay Receiver listens on port 5000 by default."
        echo "  Disable it: System Settings -> General -> AirDrop & Handoff -> AirPlay Receiver -> Off"
        echo "  Or rerun this script with a different port:"
        echo "      ./polaris_mac_launch.sh --port 5050"
    else
        echo
        echo "  Stop the offending process or rerun with: ./polaris_mac_launch.sh --port <NUM>"
    fi
    exit 1
}

# -----------------------------------------------------------------------------
# Runtime detection
# -----------------------------------------------------------------------------
docker_available() {
    command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1
}

# Returns 0 if the docker CLI is installed (regardless of whether the daemon is up)
docker_cli_present() {
    command -v docker >/dev/null 2>&1
}

# Returns 0 if Docker Desktop.app is installed in /Applications
docker_desktop_installed() {
    [[ -d "/Applications/Docker.app" || -d "$HOME/Applications/Docker.app" ]]
}

# Try to bring the Docker daemon up. If Docker Desktop is installed, launch it
# and wait up to 90s for the daemon socket to respond. Returns 0 on success.
ensure_docker_running() {
    if docker_available; then return 0; fi

    if ! docker_cli_present; then
        return 1
    fi

    if ! docker_desktop_installed; then
        warn "Docker CLI is installed but Docker Desktop.app was not found in /Applications."
        echo "   Start your Docker daemon however you usually do, then retry."
        return 1
    fi

    log "Docker daemon is not running. Launching Docker Desktop..."
    open -a Docker 2>/dev/null || true

    printf "%s>%s waiting for Docker daemon " "$CYAN" "$NC"
    local deadline=$(( $(date +%s) + 90 ))
    while (( $(date +%s) < deadline )); do
        if docker info >/dev/null 2>&1; then
            printf " %s[ok]%s\n" "$GREEN" "$NC"
            return 0
        fi
        printf "."
        sleep 3
    done
    printf " %s[timeout]%s\n" "$RED" "$NC"
    warn "Docker Desktop did not become ready within 90s."
    echo "   Open Docker Desktop manually and wait for the menu-bar whale to stop animating, then retry."
    return 1
}

docker_app_running() {
    (cd "$WEB_DIR" && docker compose ps --services --filter status=running 2>/dev/null) | grep -q '^app$'
}

# A container can be marked "running" by docker compose for a moment while
# it's actually in a crash-restart loop (gunicorn worker-boot failure, broken
# image, missing module). For the launcher's "already up — skip rebuild"
# decision, we want a stricter check: the app actually answers HTTP.
docker_app_healthy() {
    docker_app_running || return 1
    curl --fail --silent --max-time 3 "http://localhost:$PORT/login" >/dev/null 2>&1
}

native_running() {
    [[ -f "$PID_FILE" ]] || return 1
    local pid
    pid="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [[ -z "$pid" ]]; then return 1; fi
    kill -0 "$pid" 2>/dev/null
}

# Compare image creation time to source mtime; if any source file is newer,
# the running container is serving stale code and should be rebuilt.
docker_image_stale() {
    local img_created src_epoch img_epoch
    img_created="$(docker inspect --format '{{.Created}}' polaris_web-app 2>/dev/null \
                || docker inspect --format '{{.Created}}' polaris-web-app 2>/dev/null \
                || docker inspect --format '{{.Created}}' polaris-app 2>/dev/null \
                || echo '')"
    if [[ -z "$img_created" ]]; then return 0; fi   # no image, treat as stale
    img_epoch="$(date -j -f "%Y-%m-%dT%H:%M:%S" "${img_created%.*}" +%s 2>/dev/null \
              || date -d "$img_created" +%s 2>/dev/null \
              || echo 0)"
    if [[ "$img_epoch" -eq 0 ]]; then return 0; fi
    src_epoch="$(find "$WEB_DIR" -type f \
                  ! -path '*/venv/*' ! -path '*/__pycache__/*' ! -path '*/.git/*' \
                  -exec stat -f '%m' {} \; 2>/dev/null \
              | sort -nr | head -1)"
    if [[ -z "$src_epoch" ]]; then
        src_epoch="$(find "$WEB_DIR" -type f \
                      ! -path '*/venv/*' ! -path '*/__pycache__/*' ! -path '*/.git/*' \
                      -printf '%T@\n' 2>/dev/null | cut -d. -f1 | sort -nr | head -1)"
    fi
    if [[ -z "$src_epoch" ]]; then return 1; fi
    (( src_epoch > img_epoch )) || return 1
    return 0
}

clear_stale_pid() {
    if [[ -f "$PID_FILE" ]] && ! native_running; then
        rm -f "$PID_FILE"
    fi
}

# v8.56: rotate the Flask session secret on every fresh launch so
# prior session cookies are invalidated and the browser is forced
# back to /login. Called by launch_docker, rebuild_docker, and
# launch_native — all three paths that bring a Polaris instance up.
#
# Skipped only if the operator explicitly set POLARIS_SECRET_KEY in
# their shell env (stable-session development workflow). Without this
# rotation, container restarts inherit the same hardcoded compose key
# (`dev-secret-rotate-in-production`) and users stay logged in across
# relaunches — a real auth-hygiene concern even in dev.
#
# Generation methods in fallback order:
#   1. openssl rand -hex 32  (universal; preferred)
#   2. python3 secrets.token_hex(32)
#   3. /dev/urandom + xxd  (last-resort; macOS always has both)
rotate_session_secret_if_unset() {
    if [ -n "${POLARIS_SECRET_KEY:-}" ]; then
        log "Honoring POLARIS_SECRET_KEY from shell env (stable session mode)"
        return 0
    fi

    # v8.100: persist the secret in $STATE_DIR/secret_key so sessions
    # survive across launcher invocations. Pre-v8.100 every double-click
    # of the launcher rotated the secret and silently invalidated all
    # prior browser tabs — the user saw "sometimes I'm logged in,
    # sometimes I'm at /login" with no obvious cause. The v8.56/v8.58
    # defense (rotate to invalidate leaked cookies) is preserved as an
    # explicit operator action: `rm /tmp/polaris-state/secret_key` then
    # relaunch.
    local state_dir="${POLARIS_STATE_DIR:-/tmp/polaris-state}"
    local secret_file="$state_dir/secret_key"
    mkdir -p "$state_dir"

    if [ -f "$secret_file" ] && [ -s "$secret_file" ]; then
        POLARIS_SECRET_KEY="$(cat "$secret_file")"
        export POLARIS_SECRET_KEY
        log "Loaded persistent session secret from $secret_file"
        return 0
    fi

    if command -v openssl >/dev/null 2>&1; then
        POLARIS_SECRET_KEY="$(openssl rand -hex 32)"
    elif command -v python3 >/dev/null 2>&1; then
        POLARIS_SECRET_KEY="$(python3 -c 'import secrets;print(secrets.token_hex(32))')"
    else
        POLARIS_SECRET_KEY="$(head -c 32 /dev/urandom | xxd -p -c 64)"
    fi

    # Mode 0600 — owner read/write only. /tmp is multi-user on macOS.
    ( umask 077; printf '%s' "$POLARIS_SECRET_KEY" > "$secret_file" )
    chmod 600 "$secret_file" 2>/dev/null || true
    export POLARIS_SECRET_KEY
    log "Generated + persisted session secret to $secret_file"
    log "(rm this file + relaunch to force-rotate; v8.56 defense preserved)"
}

open_browser() {
    local url="$1"
    if command -v open >/dev/null 2>&1; then
        open "$url" 2>/dev/null || true
    else
        warn "Open this URL in your browser: $url"
    fi
}

# -----------------------------------------------------------------------------
# Health check loop with clean progress
# -----------------------------------------------------------------------------
wait_for_url() {
    local url="$1" label="$2" deadline=$(( $(date +%s) + HEALTH_TIMEOUT ))
    printf "%s>%s waiting for %s " "$CYAN" "$NC" "$label"
    while (( $(date +%s) < deadline )); do
        if curl -fsS --max-time 2 "$url" >/dev/null 2>&1; then
            printf " %s[ok]%s\n" "$GREEN" "$NC"
            return 0
        fi
        printf "."
        sleep 2
    done
    printf " %s[timeout]%s\n" "$RED" "$NC"
    return 1
}

# -----------------------------------------------------------------------------
# Docker path
# -----------------------------------------------------------------------------
launch_docker() {
    require_layout
    cd "$WEB_DIR"

    local force_rebuild="${1:-0}"

    if docker_app_healthy; then
        if [[ "$force_rebuild" == "1" ]] || docker_image_stale; then
            warn "Running image is older than your source files. Rebuilding."
            log "Stopping current stack"
            docker compose down
        else
            # v8.58: Even when the image + stack are healthy and up-to-date,
            # rotate the session secret and recreate the app container so the
            # new key takes effect. This enforces the v8.56 security posture
            # (fresh /login on every launcher invocation) even when the
            # launcher would otherwise short-circuit to "already running."
            # Pre-v8.58 the early return below skipped rotation entirely,
            # so re-running Polaris.command without an explicit logout left
            # the prior session cookie valid → user landed on the dashboard.
            ok "Polaris stack already running and up-to-date"
            rotate_session_secret_if_unset
            log "Recreating app container so the rotated secret takes effect"
            POLARIS_HOST_PORT="$PORT" docker compose up -d --force-recreate --no-deps app
            wait_for_url "http://localhost:$PORT/login" "web app on :$PORT" || true
            echo "   To force a full rebuild:    ./polaris_mac_launch.sh rebuild"
            echo "   If your browser shows old assets, hard-refresh with Cmd+Shift+R"
            echo "   or open the site in a private window."
            open_browser "http://localhost:$PORT/"
            print_credentials
            return 0
        fi
    elif docker_app_running; then
        warn "App container is running but not responding (likely crash-loop)."
        log "Tearing down for a clean rebuild"
        docker compose down
    fi

    rotate_session_secret_if_unset
    docker_compose_up_with_heal
    ok "Polaris is LIVE at http://localhost:$PORT"
    print_credentials
    open_browser "http://localhost:$PORT/"
    print_post_launch_hints docker
}

# Returns 0 if the postgres container has logged a password-auth failure for
# the polaris_app user. This is the signature of a stale data volume that was
# initialized with a different password than the one the app is now configured
# to use. Self-healing in this case = wipe the volume and let init re-run.
db_auth_broken() {
    docker compose logs --tail 200 db 2>&1 \
        | grep -q 'password authentication failed for user "polaris_app"'
}

# Bring the stack up. If the app fails to come healthy AND the db logs show
# auth failure, wipe the volume and retry once. This makes stale-volume drift
# self-correcting instead of producing an opaque 500 on the first login.
docker_compose_up_with_heal() {
    log "Bringing up Docker stack (Postgres 16 + Flask)"
    POLARIS_HOST_PORT="$PORT" docker compose up -d --build

    log "Waiting for database health"
    local deadline=$(( $(date +%s) + HEALTH_TIMEOUT ))
    while (( $(date +%s) < deadline )); do
        if docker compose exec -T db pg_isready -U postgres -d polaris_test >/dev/null 2>&1; then
            ok "Database healthy"; break
        fi
        sleep 3
    done

    if wait_for_url "http://localhost:$PORT/login" "web app on :$PORT"; then
        return 0
    fi

    # Health check failed. Determine why before giving up.
    if db_auth_broken; then
        warn "Detected stale-volume auth failure. Wiping pgdata and reinitializing."
        docker compose down -v
        log "Rebuilding stack from a fresh database volume"
        POLARIS_HOST_PORT="$PORT" docker compose up -d --build

        log "Waiting for database health (retry)"
        deadline=$(( $(date +%s) + HEALTH_TIMEOUT ))
        while (( $(date +%s) < deadline )); do
            if docker compose exec -T db pg_isready -U postgres -d polaris_test >/dev/null 2>&1; then
                ok "Database healthy"; break
            fi
            sleep 3
        done

        if wait_for_url "http://localhost:$PORT/login" "web app on :$PORT (retry)"; then
            ok "Auto-heal succeeded — fresh database volume in place."
            return 0
        fi
    fi

    err "Web app failed to start. View logs: ./polaris_mac_launch.sh logs app"
    err "Or wipe everything and start over: ./polaris_mac_launch.sh nuke"
    exit 1
}

# -----------------------------------------------------------------------------
# Native path
# -----------------------------------------------------------------------------
launch_native() {
    require_layout

    if native_running; then
        # v8.58: same fix as launch_docker — when native gunicorn is
        # already running, the pre-v8.58 early-return left the existing
        # process (with its baked-in SECRET_KEY) untouched, so the user's
        # session cookie survived. Kill it and fall through to the normal
        # start path so rotate_session_secret_if_unset (line ~537 below)
        # generates a fresh key and gunicorn picks it up at startup.
        local prev_pid
        prev_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
        log "Native Polaris already running (pid $prev_pid) — restarting to rotate session secret"
        if [[ -n "$prev_pid" ]]; then
            kill "$prev_pid" 2>/dev/null || true
            sleep 1
            if kill -0 "$prev_pid" 2>/dev/null; then
                warn "PID $prev_pid still alive, sending SIGKILL"
                kill -9 "$prev_pid" 2>/dev/null || true
            fi
        fi
        rm -f "$PID_FILE"
    fi
    clear_stale_pid

    if ! command -v brew >/dev/null 2>&1; then
        err "Homebrew is required for the native path."
        echo '   Install: /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
        exit 1
    fi

    log "Installing prereqs via Homebrew (postgresql@16, python@3.12)"
    brew install postgresql@16 python@3.12

    # v9.02: Homebrew installs postgresql@16 keg-only — its bin/ dir
    # is NOT in PATH after `brew install` because it would conflict
    # with other postgres versions if any. The launcher needs psql,
    # createdb, dropdb to be findable; prepend the keg-only bin
    # for the rest of this script's lifetime. Idempotent (no harm
    # if PATH already includes it).
    if [ -d /opt/homebrew/opt/postgresql@16/bin ]; then
        export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"
    elif [ -d /usr/local/opt/postgresql@16/bin ]; then
        # Intel Mac Homebrew prefix
        export PATH="/usr/local/opt/postgresql@16/bin:$PATH"
    fi

    if ! brew services list | grep -E '^postgresql@16' | grep -q started; then
        log "Starting PostgreSQL 16"
        brew services start postgresql@16
        sleep 3
    fi

    if ! psql -U "$USER" -lqt 2>/dev/null | cut -d'|' -f1 | grep -qw polaris_test; then
        log "Creating polaris_test database"
        createdb polaris_test
    fi

    log "Loading Polaris schema, sample data, procedures, triggers, grants"
    (cd "$SQL_DIR" && psql -d polaris_test -v ON_ERROR_STOP=1 -f 00_load_all.sql >/dev/null) || {
        err "Schema load failed. Inspect: psql -d polaris_test -f $SQL_DIR/00_load_all.sql"
        exit 1
    }
    ok "Database ready (schema + sample data + grants)"

    # v8.99: apply v8.95+v8.97 schema migrations on top of the v0 baseline.
    # 00_load_all.sql creates the schema_version registry but does not
    # apply migrations; without this step OperatorWebauthnCredential
    # doesn't exist and the v8.97 WebAuthn surface 500s on first use.
    log "Applying schema migrations (v8.95 framework)"
    POLARIS_DB_NAME=polaris_test POLARIS_DB_USER="$USER" POLARIS_DB_HOST=localhost \
        "$SCRIPT_DIR/scripts/polaris-migrate.sh" --up >/dev/null || {
        err "Migration apply failed. Inspect: $SCRIPT_DIR/scripts/polaris-migrate.sh --status"
        exit 1
    }
    ok "Migrations applied"

    cd "$WEB_DIR"
    if [[ ! -d venv ]]; then
        log "Creating Python virtual environment"
        python3.12 -m venv venv
    fi
    # shellcheck disable=SC1091
    source venv/bin/activate

    log "Installing Python dependencies"
    # v8.99: webauthn pulled in for the Position B MFA surface (sanctum/
    # 2026-05-14-webauthn-operator-auth.md). Pure-Python; ~6MB; one direct dep.
    pip install --quiet --disable-pip-version-check flask psycopg2-binary gunicorn werkzeug webauthn

    # v8.99: macOS fork-safety opt-out for hashlib.scrypt in forked workers.
    # Without this, password verification crashes the worker with
    # "objc[…]: +[NSCharacterSet initialize] may have been in progress in
    # another thread when fork() was called". Dev-only; production docker
    # path doesn't fork from a macOS objc-loaded parent.
    export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES

    rotate_session_secret_if_unset
    log "Starting gunicorn on :$PORT (logs: $LOG_FILE)"
    : > "$LOG_FILE"
    nohup gunicorn --bind "0.0.0.0:$PORT" \
                   --workers 2 --timeout 120 \
                   --access-logfile "$LOG_FILE" \
                   --error-logfile "$LOG_FILE" \
                   app:app >> "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    disown 2>/dev/null || true

    if ! wait_for_url "http://localhost:$PORT/login" "gunicorn on :$PORT"; then
        err "App failed to start. Tail logs: tail -f $LOG_FILE"
        exit 1
    fi

    ok "Native Polaris running at http://localhost:$PORT (pid $(cat "$PID_FILE"))"
    print_credentials
    open_browser "http://localhost:$PORT/"
    print_post_launch_hints native
}

# -----------------------------------------------------------------------------
# Stop, status, logs, reset, test
# -----------------------------------------------------------------------------
stop_all() {
    banner
    local stopped=0

    if docker_available; then
        if docker_app_running; then
            log "Stopping Docker stack"
            (cd "$WEB_DIR" && docker compose down)
            ok "Docker stack stopped"
            stopped=1
        fi
    fi

    if native_running; then
        local pid
        pid="$(cat "$PID_FILE")"
        log "Stopping native gunicorn (pid $pid)"
        kill "$pid" 2>/dev/null || true
        sleep 1
        if kill -0 "$pid" 2>/dev/null; then
            warn "PID $pid still alive, sending SIGKILL"
            kill -9 "$pid" 2>/dev/null || true
        fi
        rm -f "$PID_FILE"
        ok "Native gunicorn stopped"
        stopped=1
    fi

    clear_stale_pid
    if (( stopped == 0 )); then
        warn "Nothing running."
    fi
}


# -----------------------------------------------------------------------------
# Watch mode: foreground-block and tear down the stack when the browser closes
# -----------------------------------------------------------------------------
# State dir is bind-mounted into the container by docker-compose so both the
# host launcher and the Flask process read/write the same files.
STATE_DIR="${POLARIS_STATE_DIR:-/tmp/polaris-state}"
HEARTBEAT_FILE="$STATE_DIR/heartbeat"
QUIT_FILE="$STATE_DIR/quit"

prepare_state_dir() {
    mkdir -p "$STATE_DIR" 2>/dev/null || true
    chmod 777 "$STATE_DIR" 2>/dev/null || true
    rm -f "$HEARTBEAT_FILE" "$QUIT_FILE" 2>/dev/null || true
}

# Get the modification time of a file as a Unix timestamp. Portable across
# macOS (BSD stat) and Linux (GNU stat) — `stat -f` means completely different
# things on the two systems, so we have to detect the kernel.
file_mtime() {
    local f="$1"
    [[ -e "$f" ]] || { echo 0; return; }
    if [[ "$(uname)" == "Darwin" ]]; then
        stat -f %m "$f" 2>/dev/null || echo 0
    else
        stat -c %Y "$f" 2>/dev/null || echo 0
    fi
}

watch_browser_presence() {
    # v8.51: raised default from 45s → 180s. The old 45s window was too
    # tight for real browser behavior:
    #   - Background-tab setInterval throttling (~1/min in Chrome,
    #     Safari, Firefox) → first missed heartbeat ≈ 60s, trips 45s.
    #   - Slow page transitions (admin lists at scale, /sql, UC-7
    #     warrant audit) can leave > 45s gaps during legitimate use.
    #   - Laptop sleep / VPN reconnect / lid-close trivially > 45s.
    # The heartbeat.js (v8.51) also beats on visibilitychange + focus
    # + pageshow so the first foreground-return produces a fresh
    # beat. Together: 180s threshold + foreground-return beats =
    # robust enough for real dev use, still fast enough to detect
    # closed tabs (the explicit /api/quit beacon is near-instant for
    # actual tab-close).
    local stale_threshold="${POLARIS_WATCH_STALE:-180}"  # secs without heartbeat
    local startup_grace="${POLARIS_WATCH_GRACE:-90}"     # initial wait before checking
    local poll_interval=3

    echo
    log "Watch mode active. Close the Polaris browser tab to shut down,"
    echo "   or press Ctrl+C in this terminal."
    echo

    # Trap interactive interrupts to ensure clean teardown
    trap 'echo; log "Interrupt received."; stop_all; exit 0' INT TERM HUP

    local started_at
    started_at=$(date +%s)

    while true; do
        sleep "$poll_interval"
        local now
        now=$(date +%s)

        # Explicit quit beacon from pagehide → near-instant shutdown
        if [[ -f "$QUIT_FILE" ]]; then
            rm -f "$QUIT_FILE"
            echo
            log "Browser tab closed (quit beacon received)."
            stop_all
            exit 0
        fi

        # Inside startup grace, don't apply staleness check yet — give the
        # user time to actually click into the browser tab and start beating.
        if (( now - started_at < startup_grace )); then
            continue
        fi

        # Heartbeat staleness check (browser crashed or ran out of network)
        local hb_mtime
        hb_mtime=$(file_mtime "$HEARTBEAT_FILE")
        if (( hb_mtime == 0 )); then
            # Never had a heartbeat after grace expired → user never opened tab
            echo
            warn "Grace window expired with no browser heartbeat."
            log "Stack stays up. Open http://localhost:$PORT yourself, or Ctrl+C to stop."
            # Reset so we keep watching for a heartbeat to arrive
            started_at=$now
            continue
        fi
        local hb_age=$(( now - hb_mtime ))
        if (( hb_age > stale_threshold )); then
            echo
            log "No browser heartbeat for ${hb_age}s. Assuming tab closed."
            stop_all
            exit 0
        fi
    done
}

status() {
    banner
    if docker_available; then
        if docker_app_running; then
            ok "Docker stack: UP"
            (cd "$WEB_DIR" && docker compose ps)
        else
            warn "Docker stack: not running"
        fi
    else
        warn "Docker: not installed or not running"
    fi
    echo
    if native_running; then
        ok "Native gunicorn: UP (pid $(cat "$PID_FILE"))"
        echo "   Logs: $LOG_FILE"
    else
        warn "Native gunicorn: not running"
    fi
    echo
    if command -v lsof >/dev/null 2>&1 && port_in_use "$PORT"; then
        echo "   Port $PORT owner: $(port_owner "$PORT")"
    fi
}

# Read-only diagnostic. Reports the state of every component the launcher
# depends on, without modifying anything. Use this when something looks wrong
# and you want to know what the script *thinks* the world looks like.
doctor() {
    banner
    printf "%sPOLARIS DOCTOR — READ-ONLY DIAGNOSTIC%s\n" "$BOLD" "$NC"
    echo

    # 1. Layout
    printf "%sFolder layout%s\n" "$BOLD" "$NC"
    for d in "$WEB_DIR" "$SQL_DIR" "$CLI_DIR"; do
        if [[ -d "$d" ]]; then
            printf "  ${GREEN}OK${NC}    %s\n" "$d"
        else
            printf "  ${RED}MISS${NC}  %s\n" "$d"
        fi
    done
    echo

    # 2. Critical files + permissions
    printf "%sCritical files + permissions%s\n" "$BOLD" "$NC"
    for spec in \
        "$WEB_DIR/Dockerfile:exec=no" \
        "$WEB_DIR/docker-compose.yml:exec=no" \
        "$WEB_DIR/docker-init.sh:exec=yes" \
        "$WEB_DIR/app.py:exec=no" \
        "$WEB_DIR/security.py:exec=no" \
        "$WEB_DIR/templates/atlas.html:exec=no" \
        "$WEB_DIR/templates/dashboard.html:exec=no" \
        "$WEB_DIR/static/atlas-globe.js:exec=no" \
        "$WEB_DIR/static/polaris.css:exec=no" \
        "$SCRIPT_DIR/polaris_mac_launch.sh:exec=yes" \
        "$SCRIPT_DIR/Polaris.command:exec=yes" \
        "$SQL_DIR/00_load_all.sql:exec=no" ; do
        local path="${spec%%:*}"
        local need_exec="${spec##*=}"
        if [[ ! -e "$path" ]]; then
            printf "  ${RED}MISS${NC}  %s\n" "$path"
            continue
        fi
        if [[ "$need_exec" == "yes" ]]; then
            if [[ -x "$path" ]]; then
                printf "  ${GREEN}OK${NC}    %s (executable)\n" "$path"
            else
                printf "  ${YELLOW}WARN${NC}  %s — needs +x  (run: chmod +x %s)\n" "$path" "$path"
            fi
        else
            printf "  ${GREEN}OK${NC}    %s\n" "$path"
        fi
    done
    echo

    # 3. Dockerfile sanity (the most common silent failure)
    printf "%sDockerfile content sanity%s\n" "$BOLD" "$NC"
    if [[ -f "$WEB_DIR/Dockerfile" ]]; then
        if grep -q "COPY .*security.py" "$WEB_DIR/Dockerfile"; then
            printf "  ${GREEN}OK${NC}    Dockerfile copies security.py\n"
        else
            printf "  ${RED}BAD${NC}   Dockerfile does NOT copy security.py — image will crash\n"
            printf "        Add 'security.py' to the COPY app.py line in Dockerfile\n"
        fi
    fi
    echo

    # 4. Docker subsystem
    printf "%sDocker subsystem%s\n" "$BOLD" "$NC"
    if docker_cli_present; then
        local ver
        ver="$(docker --version 2>/dev/null)"
        printf "  ${GREEN}OK${NC}    Docker CLI: %s\n" "$ver"
        if docker_available; then
            printf "  ${GREEN}OK${NC}    Docker daemon: running\n"
        else
            printf "  ${YELLOW}WARN${NC}  Docker daemon: NOT running (Docker Desktop must be open)\n"
        fi
        if docker_desktop_installed; then
            printf "  ${GREEN}OK${NC}    Docker Desktop.app: installed\n"
        else
            printf "  ${YELLOW}WARN${NC}  Docker Desktop.app not in /Applications\n"
        fi
    else
        printf "  ${YELLOW}WARN${NC}  Docker CLI not installed (native fallback will be used)\n"
    fi
    echo

    # 5. Polaris containers (if Docker is up)
    if docker_available; then
        printf "%sPolaris containers%s\n" "$BOLD" "$NC"
        local containers
        containers="$(docker ps -a --filter name=polaris --format 'table {{.Names}}\t{{.Status}}' 2>/dev/null)"
        if [[ -n "$containers" ]] && [[ "$(echo "$containers" | wc -l)" -gt 1 ]]; then
            echo "$containers" | sed 's/^/  /'
            # If app container is in restart loop, flag it
            if docker ps --filter name=polaris-app --filter status=restarting --format '{{.Names}}' 2>/dev/null | grep -q polaris-app; then
                printf "  ${RED}BAD${NC}   polaris-app is in a restart loop — run: ./polaris_mac_launch.sh logs app\n"
            fi
        else
            printf "  ${YELLOW}WARN${NC}  No polaris containers (stack is down)\n"
        fi
        echo
        printf "%sPolaris volumes%s\n" "$BOLD" "$NC"
        local vols
        vols="$(docker volume ls --filter name=polaris --format '{{.Name}}' 2>/dev/null)"
        if [[ -n "$vols" ]]; then
            echo "$vols" | sed 's/^/  /'
        else
            printf "  ${YELLOW}WARN${NC}  No polaris volumes (will be created on next 'up')\n"
        fi
        echo
    fi

    # 6. Port + URL state
    printf "%sPort + service state%s\n" "$BOLD" "$NC"
    if command -v lsof >/dev/null 2>&1; then
        if port_in_use "$PORT"; then
            printf "  Port %s: in use by %s\n" "$PORT" "$(port_owner "$PORT")"
        else
            printf "  Port %s: free\n" "$PORT"
        fi
    fi
    if curl -fsS -m 2 "http://localhost:$PORT/login" >/dev/null 2>&1; then
        printf "  ${GREEN}OK${NC}    http://localhost:$PORT/login responds with 200\n"
    else
        printf "  ${YELLOW}WARN${NC}  http://localhost:$PORT/login does not respond\n"
    fi
    echo

    # 7. Stale-volume auth check (if Docker is up + db running)
    if docker_available && docker compose -f "$WEB_DIR/docker-compose.yml" ps --services --filter status=running 2>/dev/null | grep -q '^db$'; then
        printf "%sDatabase auth state%s\n" "$BOLD" "$NC"
        if db_auth_broken; then
            printf "  ${RED}BAD${NC}   Postgres logs show password-auth failure for polaris_app\n"
            printf "        This is a stale-volume drift. Fix:\n"
            printf "          ./polaris_mac_launch.sh rebuild   (auto-heals)\n"
            printf "          OR: ./polaris_mac_launch.sh nuke    (full wipe)\n"
        else
            printf "  ${GREEN}OK${NC}    No auth failures detected in db logs\n"
        fi
        echo
    fi

    # 8. Watch mode state
    printf "%sWatch mode state%s\n" "$BOLD" "$NC"
    if [[ -f "$HEARTBEAT_FILE" ]]; then
        local age=$(( $(date +%s) - $(file_mtime "$HEARTBEAT_FILE") ))
        printf "  Heartbeat:    last %ds ago\n" "$age"
    else
        printf "  Heartbeat:    no file (browser hasn't connected yet)\n"
    fi
    if [[ -f "$QUIT_FILE" ]]; then
        printf "  Quit beacon:  present (browser tab closed)\n"
    else
        printf "  Quit beacon:  absent\n"
    fi
    echo

    printf "%sNext steps based on what you see%s\n" "$BOLD" "$NC"
    if curl -fsS -m 2 "http://localhost:$PORT/login" >/dev/null 2>&1; then
        printf "  Polaris is reachable. Open: %shttp://localhost:%s/%s\n" "$CYAN" "$PORT" "$NC"
    elif docker_app_running; then
        printf "  Stack is up but not responding. Try: ./polaris_mac_launch.sh logs app\n"
    elif docker_available; then
        printf "  Stack is down. Bring it up: ./polaris_mac_launch.sh up\n"
    else
        printf "  Docker is not running. Start Docker Desktop, then: ./polaris_mac_launch.sh up\n"
    fi
}

logs() {
    local svc="${1:-app}"
    if docker_app_running; then
        (cd "$WEB_DIR" && docker compose logs -f "$svc")
    elif native_running; then
        if [[ -f "$LOG_FILE" ]]; then
            tail -f "$LOG_FILE"
        else
            err "No native log file at $LOG_FILE"
            exit 1
        fi
    else
        err "Nothing running. Start with: ./polaris_mac_launch.sh up"
        exit 1
    fi
}

reset_all() {
    banner
    warn "This will drop the Docker volume and stop the native instance."
    printf "Continue? [y/N] "
    read -r ans
    if [[ "$ans" != "y" && "$ans" != "Y" ]]; then
        echo "Aborted."
        exit 0
    fi
    if docker_available; then
        log "Tearing down Docker stack and dropping volume"
        (cd "$WEB_DIR" && docker compose down -v) || true
    fi
    if native_running; then
        kill "$(cat "$PID_FILE")" 2>/dev/null || true
        rm -f "$PID_FILE"
    fi
    rm -f "$LOG_FILE"
    clear_stale_pid
    ok "Reset complete. Run './polaris_mac_launch.sh up' to start fresh."
}

run_tests() {
    banner
    require_layout
    if docker_app_running; then
        log "Running web tests inside Docker container"
        (cd "$WEB_DIR" && docker compose exec -T app python3 test_app.py)
        echo
        log "Running CLI tests on host (CLI is not in the container build context)"
        (cd "$CLI_DIR" && python3 test_cli.py) || warn "CLI tests reported failures"
        ok "Test run complete"
    elif native_running; then
        log "Running web tests against native instance"
        (cd "$WEB_DIR" && source venv/bin/activate && python3 test_app.py)
        echo
        log "Running CLI tests"
        (cd "$CLI_DIR" && python3 test_cli.py) || warn "CLI tests reported failures"
        ok "Test run complete"
    else
        err "No running Polaris instance. Start with: ./polaris_mac_launch.sh up"
        exit 1
    fi
}

# Force a clean rebuild of the Docker image (picks up new static files,
# templates, app code). Does NOT drop the Postgres volume by default — but
# self-heals if the new app can't auth against the existing volume.
rebuild_docker() {
    banner
    require_layout
    if ! ensure_docker_running; then
        err "Docker is not running and could not be started automatically."
        echo "   Options:"
        echo "     1. Open Docker Desktop manually, then run: ./polaris_mac_launch.sh rebuild"
        echo "     2. Use the native path (no Docker):        ./polaris_mac_launch.sh up --native"
        exit 1
    fi
    log "Stopping stack"
    (cd "$WEB_DIR" && docker compose down) || true
    log "Rebuilding image with --no-cache"
    cd "$WEB_DIR"
    POLARIS_HOST_PORT="$PORT" docker compose build --no-cache app

    rotate_session_secret_if_unset
    docker_compose_up_with_heal

    ok "Polaris rebuilt and live at http://localhost:$PORT"
    echo
    warn "Browser cache or session cookie may still show stale state."
    echo "  Hard-refresh:  Cmd+Shift+R"
    echo "  Or open the site in a Private/Incognito window."
    echo
    print_credentials
    open_browser "http://localhost:$PORT/"
}

# Total reset: stop, remove containers, remove image, drop volumes.
# Use this when the stack is in a state you can't reason about.
nuke_all() {
    banner
    warn "This will destroy:"
    echo "    - all polaris containers (running and stopped)"
    echo "    - the polaris_web-app Docker image"
    echo "    - the polaris-pgdata volume (database wiped)"
    echo "    - any native gunicorn process"
    echo "    - the runtime state directory"
    echo
    log "Proceeding in 2 seconds. Ctrl+C to abort."
    sleep 2

    if docker_cli_present && docker_available; then
        log "docker compose down -v"
        (cd "$WEB_DIR" && docker compose down -v --remove-orphans) || true

        log "Removing any lingering polaris containers"
        docker ps -aq --filter name=polaris | xargs -r docker rm -f 2>/dev/null || true

        log "Removing polaris_web-app image"
        docker rmi -f polaris_web-app:latest 2>/dev/null || true
        docker rmi -f polaris_web-app 2>/dev/null || true

        log "Pruning dangling polaris volumes"
        docker volume ls -q --filter name=polaris | xargs -r docker volume rm -f 2>/dev/null || true
    else
        warn "Docker is not available; skipping container/image/volume teardown."
    fi

    if native_running; then
        log "Stopping native gunicorn"
        local pid; pid="$(cat "$PID_FILE" 2>/dev/null)"
        [ -n "$pid" ] && kill -9 "$pid" 2>/dev/null || true
        rm -f "$PID_FILE"
    fi

    rm -rf "$STATE_DIR" 2>/dev/null || true

    ok "Polaris fully wiped. Ready for a fresh start:"
    echo "    ./polaris_mac_launch.sh up"
}

# -----------------------------------------------------------------------------
# Output helpers
# -----------------------------------------------------------------------------
print_credentials() {
    echo
    printf "%sDefault credentials (DEV ONLY, rotate before production):%s\n" "$BOLD" "$NC"
    printf "  %sadmin%s    / Admin@123!     full access + SQL console\n"      "$GREEN" "$NC"
    printf "  %soperator%s / Operator@123!  issue/activate/bind tokens\n"     "$GREEN" "$NC"
    printf "  %sauditor%s  / Auditor@123!   read-only + warrant audits\n"     "$GREEN" "$NC"
    echo
}

print_post_launch_hints() {
    local mode="$1"
    printf "%sCommands:%s\n" "$BOLD" "$NC"
    printf "  ./polaris_mac_launch.sh status     show what is running\n"
    printf "  ./polaris_mac_launch.sh logs       tail logs\n"
    printf "  ./polaris_mac_launch.sh test       run full test suite\n"
    printf "  ./polaris_mac_launch.sh stop       graceful shutdown\n"
    printf "  ./polaris_mac_launch.sh reset      drop volumes, full clean\n"
    if [[ "$mode" == "docker" ]]; then
        printf "%s%sDocker shortcuts:%s\n" "$DIM" "$BOLD" "$NC"
        printf "%s  cd polaris_web && docker compose logs -f app%s\n" "$DIM" "$NC"
        printf "%s  cd polaris_web && docker compose exec app sh%s\n" "$DIM" "$NC"
    fi
    echo
    printf "%sExplore the Atlas at /atlas for the operational view.%s\n" "$BOLD" "$NC"
    printf "%sDocs: README.md  /  Security: docs/operator/SECURITY.md%s\n" "$DIM" "$NC"
    echo
}

usage() {
    sed -n '2,42p' "$0" | sed 's/^# \{0,1\}//'
}

# -----------------------------------------------------------------------------
# Argument parsing
# -----------------------------------------------------------------------------
COMMAND="up"
FORCE_RUNTIME=""
DETACH=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        up|stop|status|logs|test|reset|rebuild|nuke|doctor)
            COMMAND="$1"; shift ;;
        --test)
            COMMAND="test"; shift ;;
        --rebuild)
            COMMAND="rebuild"; shift ;;
        --port)
            PORT="$2"; shift 2 ;;
        --port=*)
            PORT="${1#--port=}"; shift ;;
        --native)
            FORCE_RUNTIME="native"; shift ;;
        --docker)
            FORCE_RUNTIME="docker"; shift ;;
        --detach|--no-watch)
            DETACH=1; shift ;;
        -h|--help|help)
            usage; exit 0 ;;
        *)
            # Trailing arg may be a service name for "logs"
            if [[ "$COMMAND" == "logs" ]]; then
                LOG_SVC="$1"; shift
            else
                err "Unknown argument: $1"
                usage; exit 1
            fi
            ;;
    esac
done

# -----------------------------------------------------------------------------
# Dispatch
# -----------------------------------------------------------------------------
case "$COMMAND" in
    up)
        banner
        clear_stale_pid
        preflight_port
        prepare_state_dir
        if [[ "$FORCE_RUNTIME" == "native" ]]; then
            launch_native
        elif [[ "$FORCE_RUNTIME" == "docker" ]]; then
            if ! ensure_docker_running; then
                err "Docker not available; cannot honor --docker."
                echo "   Run without --docker to fall back to native, or open Docker Desktop and retry."
                exit 1
            fi
            launch_docker
        elif docker_cli_present; then
            if ensure_docker_running; then
                launch_docker
            else
                warn "Continuing with the native path."
                launch_native
            fi
        else
            warn "Docker not installed; using native path (slower first run)"
            launch_native
        fi
        if (( DETACH == 0 )); then
            watch_browser_presence
        else
            log "Detached mode: stack stays up after this script returns."
            log "Stop later with: ./polaris_mac_launch.sh stop"
        fi
        ;;
    stop)    stop_all ;;
    status)  status ;;
    doctor)  doctor ;;
    logs)    logs "${LOG_SVC:-app}" ;;
    test)    run_tests ;;
    reset)   reset_all ;;
    nuke)    nuke_all ;;
    rebuild)
        prepare_state_dir
        rebuild_docker
        if (( DETACH == 0 )); then
            watch_browser_presence
        else
            log "Detached mode: stack stays up after this script returns."
            log "Stop later with: ./polaris_mac_launch.sh stop"
        fi
        ;;
    *)       usage; exit 1 ;;
esac
