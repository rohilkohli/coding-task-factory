FROM python:3.12-slim@sha256:191083cdf6c7bda8c76158983163ead5d5cf7b77cf3033e805bb0f5296f51b4b

# Verifier image: pristine upstream click at the pinned commit (including its
# full test suite), with src/ removed. Only the agent's /app/src is copied in
# as an artifact, so edits to tests or config in the agent's sandbox cannot
# influence grading. A minimal dist-info registers package metadata so
# importlib.metadata.version("click") works with code loaded via PYTHONPATH.
RUN --mount=type=bind,source=vendor,target=/vendor \
    pip install --no-cache-dir --no-index --find-links /vendor/wheels pytest==8.4.1 \
    && tar -xzf /vendor/app-upstream.tar.gz -C / \
    && rm -rf /app/src \
    && site=$(python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])') \
    && mkdir -p "$site/click-8.6.0.dev0.dist-info" \
    && printf 'Metadata-Version: 2.1\nName: click\nVersion: 8.6.0.dev0\n' > "$site/click-8.6.0.dev0.dist-info/METADATA"

COPY test.sh collect_results.py grade.py f2p.txt p2p.txt /tests/
COPY defects.json partial_credit.py /tests/
RUN chmod +x /tests/test.sh

ENV PYTHONPATH=/app/src \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
