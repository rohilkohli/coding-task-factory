FROM python:3.12@sha256:9dd21fafb95870b99f9faa703a947d08feeb673048ad556e92ce503d0c086a95

# Verifier image: pristine upstream jsoncpp at the pinned commit. The library
# sources (src/lib_json) and public headers (include/) are removed; the
# agent's versions arrive as artifacts. Test sources (src/test_lib_json,
# src/jsontestrunner, test/) stay pristine, so the agent cannot alter them.
RUN --mount=type=bind,source=vendor,target=/vendor \
    tar -xzf /vendor/app-upstream.tar.gz -C / \
    && rm -rf /app/src/lib_json /app/include

COPY test.sh run_tests.py grade.py hidden_tests.cpp f2p.txt p2p.txt /tests/
RUN chmod +x /tests/test.sh

WORKDIR /app
