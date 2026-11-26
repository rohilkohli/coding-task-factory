// Usage: node brotli_tar.mjs <input.tar> <output.tar.br>
// Brotli-compresses a tar archive. Node's built-in zlib can decompress it,
// so task images need no extra tools (node:*-slim images ship without xz).
import { createReadStream, createWriteStream } from "node:fs";
import { pipeline } from "node:stream/promises";
import { constants, createBrotliCompress } from "node:zlib";

const [input, output] = process.argv.slice(2);
await pipeline(
  createReadStream(input),
  createBrotliCompress({
    params: {
      [constants.BROTLI_PARAM_QUALITY]: 9,
      [constants.BROTLI_PARAM_LGWIN]: 24,
    },
  }),
  createWriteStream(output),
);
