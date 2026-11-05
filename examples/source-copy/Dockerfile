FROM rust:1.98.1-alpine3.24 AS chef
RUN cargo install cargo-chef --version 0.1.78 --locked
WORKDIR /app

FROM chef AS planner
COPY Cargo.toml Cargo.lock ./
COPY src ./src
RUN cargo chef prepare --recipe-path recipe.json

FROM chef AS cooked
COPY --from=planner /app/recipe.json recipe.json
RUN cargo chef cook --release --recipe-path recipe.json

# Comparison: the original manifest and lockfile are still missing.
FROM cooked AS source-only-builder
COPY src ./src
RUN cargo build --release

FROM alpine:3.24 AS source-only
COPY --from=source-only-builder /app/target/release/sample /usr/local/bin/sample
ENTRYPOINT ["/usr/local/bin/sample"]

FROM source-only-builder AS touch-only-builder
RUN touch src/main.rs && cargo build --release

FROM alpine:3.24 AS touch-only
COPY --from=touch-only-builder /app/target/release/sample /usr/local/bin/sample
ENTRYPOINT ["/usr/local/bin/sample"]

# Restore the complete real project before the application build.
FROM cooked AS builder
COPY --from=planner /app/Cargo.toml /expected/Cargo.toml
COPY --from=planner /app/Cargo.lock /expected/Cargo.lock
COPY . .
RUN cmp /expected/Cargo.toml Cargo.toml && cmp /expected/Cargo.lock Cargo.lock
RUN cargo build --release --locked --bin sample

FROM alpine:3.24 AS restored
COPY --from=builder /app/target/release/sample /usr/local/bin/sample
ENTRYPOINT ["/usr/local/bin/sample"]
