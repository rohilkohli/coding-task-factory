FROM node:24-slim@sha256:873f586f3794f52281bd039bf02c048a0be08fde619338f9941bad1eb6b34530

# Offline, reproducible build. The repository snapshot (feature removed, no git
# history) and the exact test toolchain (vitest 4.1.5, typescript 5.5.4, ...)
# are vendored as Brotli-compressed tarballs and bind-mounted, so nothing is
# downloaded and the archives never land in an image layer.
RUN --mount=type=bind,source=vendor,target=/vendor \
    unbr() { node -e 'process.stdout.write(require("zlib").brotliDecompressSync(require("fs").readFileSync(process.argv[1])))' "$1"; } \
    && unbr /vendor/app-base.tar.br | tar -x -C / \
    && unbr /vendor/node_modules.tar.br | tar -x -C /app \
    && ln -s ../packages/zod /app/node_modules/zod

WORKDIR /app
