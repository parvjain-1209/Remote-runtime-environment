# Dockerfile for Multi-Language Code Runner Sandbox Image (C++, Python 3, Java 21)
FROM alpine:3.19

# Install g++, libc-dev, libstdc++, python3, and OpenJDK 21
RUN apk add --no-cache g++ libc-dev libstdc++ python3 openjdk21-jdk

# Create non-root user and group with explicit UID/GID 1000
RUN addgroup -g 1000 sandboxgroup && \
    adduser -u 1000 -G sandboxgroup -s /bin/false -D sandboxuser

# Set up sandbox working directory
WORKDIR /sandbox
RUN chown sandboxuser:sandboxgroup /sandbox

USER sandboxuser

CMD ["/bin/sh"]
