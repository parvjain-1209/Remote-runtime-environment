# Dockerfile for C++ Code Runner Sandbox Image
FROM alpine:3.19

# Install g++, libc-dev, and libstdc++
RUN apk add --no-cache g++ libc-dev libstdc++

# Create non-root user and group with explicit UID/GID 1000
RUN addgroup -g 1000 sandboxgroup && \
    adduser -u 1000 -G sandboxgroup -s /bin/false -D sandboxuser

# Set up sandbox working directory
WORKDIR /sandbox
RUN chown sandboxuser:sandboxgroup /sandbox

USER sandboxuser

CMD ["/bin/sh"]
