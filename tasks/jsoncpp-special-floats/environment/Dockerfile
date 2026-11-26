FROM python:3.12@sha256:9dd21fafb95870b99f9faa703a947d08feeb673048ad556e92ce503d0c086a95

# Toolchain from the base image: g++ 14, make, python3 (for jsoncpp's
# data-driven test script). The repository snapshot (feature removed, no git
# history) is vendored and bind-mounted, so nothing is downloaded and the
# archive never lands in an image layer.
RUN --mount=type=bind,source=vendor,target=/vendor \
    tar -xzf /vendor/app-base.tar.gz -C /

WORKDIR /app
