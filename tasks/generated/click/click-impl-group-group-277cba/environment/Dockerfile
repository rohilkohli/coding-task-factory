FROM python:3.12-slim@sha256:191083cdf6c7bda8c76158983163ead5d5cf7b77cf3033e805bb0f5296f51b4b

# Offline, reproducible build: the repository snapshot and test tooling are
# vendored next to this file and bind-mounted, so nothing is downloaded and
# the archives never land in an image layer the agent could inspect. A minimal
# dist-info registers package metadata so importlib.metadata.version("click")
# works while the code itself is loaded from /app/src via PYTHONPATH.
RUN --mount=type=bind,source=vendor,target=/vendor \
    pip install --no-cache-dir --no-index --find-links /vendor/wheels pytest==8.4.1 \
    && tar -xzf /vendor/app-base.tar.gz -C / \
    && site=$(python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])') \
    && mkdir -p "$site/click-8.6.0.dev0.dist-info" \
    && printf 'Metadata-Version: 2.1\nName: click\nVersion: 8.6.0.dev0\n' > "$site/click-8.6.0.dev0.dist-info/METADATA"

ENV PYTHONPATH=/app/src \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
