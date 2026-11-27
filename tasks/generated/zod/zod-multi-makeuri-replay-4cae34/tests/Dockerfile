FROM node:24-slim@sha256:873f586f3794f52281bd039bf02c048a0be08fde619338f9941bad1eb6b34530

# Verifier image: pristine upstream zod at the pinned commit plus the same
# vendored toolchain. Zod keeps its tests inside src/, so the pristine test
# directories are saved to /opt/pristine-tests and src/ is removed; at grading
# time the agent's src/ arrives as an artifact and test.sh puts the pristine
# tests back over it.
RUN --mount=type=bind,source=vendor,target=/vendor \
    unbr() { node -e 'process.stdout.write(require("zlib").brotliDecompressSync(require("fs").readFileSync(process.argv[1])))' "$1"; } \
    && unbr /vendor/app-upstream.tar.br | tar -x -C / \
    && unbr /vendor/node_modules.tar.br | tar -x -C /app \
    && ln -s ../packages/zod /app/node_modules/zod \
    && mkdir -p /opt/pristine-tests \
    && cd /app/packages/zod/src \
    && find . -type d -name tests -prune -exec cp -r --parents {} /opt/pristine-tests \; \
    && rm -rf /app/packages/zod/src

COPY test.sh grade.mjs f2p.txt p2p.txt /tests/
COPY defects.json partial_credit.mjs /tests/
RUN chmod +x /tests/test.sh

WORKDIR /app
