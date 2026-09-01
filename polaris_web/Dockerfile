# ============================================================================
# Polaris Web App — Container image
#
# Lightweight production-ready image:
#   - Python 3.12 slim base
#   - Flask + psycopg2 + gunicorn
#   - Non-root user
#   - Healthcheck via the dashboard route
# ============================================================================

FROM python:3.12-slim

# Install psycopg2 build deps (libpq) and clean up
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# v9.05 / Wave 1 / C3: pinned via requirements.txt (was 3 inline packages
# with loose specs). Matches polaris_web/requirements.txt + Dockerfile.prod.
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy app code:
#   anchoring.py    R10-2 Merkle helper
#   zk.py           R10-1 ZK wrapper
#   webauthn_auth.py v8.97 WebAuthn/MFA module (app.py imports it at startup)
#   __version__.py  v9.06 canonical POLARIS_VERSION source (app.py imports it)
#   observability.py v9.31 operator-readable metrics (app.py + security.py
#                    import it at startup; v9.40 fix — was missed because
#                    the regression-guard regex didn't tolerate trailing
#                    comments on the `import observability  # ...` line)
COPY app.py security.py test_app.py gunicorn.conf.py ./
COPY anchoring.py zk.py webauthn_auth.py __version__.py observability.py pqc_signing.py custody.py ./
COPY templates/ ./templates/
COPY static/   ./static/

# Run as non-root user
RUN useradd --uid 1000 --create-home polaris && chown -R polaris:polaris /app
USER polaris

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl --fail --silent http://localhost:5000/ || exit 1

# Default command runs gunicorn (production); override with `python3 app.py`
# for the Flask development server when debugging.
CMD ["gunicorn", "--config", "gunicorn.conf.py", "app:app"]
