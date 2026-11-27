FROM python:3.12-slim@sha256:191083cdf6c7bda8c76158983163ead5d5cf7b77cf3033e805bb0f5296f51b4b

# Verifier for test-writing tasks: the pristine upstream click repository
# (reference implementation and its tests/conftest.py fixtures) plus hidden
# implementation variants in /tests/variants (the defective version and
# plausible-but-wrong versions). The agent's test file arrives as an artifact
# (/app/regression) and is run against every variant by run_variants.py.
RUN --mount=type=bind,source=vendor,target=/vendor \
    pip install --no-cache-dir --no-index --find-links /vendor/wheels pytest==8.4.1 \
    && tar -xzf /vendor/app-upstream.tar.gz -C / \
    && site=$(python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])') \
    && mkdir -p "$site/click-8.6.0.dev0.dist-info" \
    && printf 'Metadata-Version: 2.1\nName: click\nVersion: 8.6.0.dev0\n' > "$site/click-8.6.0.dev0.dist-info/METADATA"

COPY test.sh run_variants.py rigor.json /tests/
COPY variants /tests/variants
RUN chmod +x /tests/test.sh

ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
