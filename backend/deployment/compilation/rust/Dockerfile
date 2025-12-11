ARG BUILD_DISTRO
FROM --platform=${TARGETPLATFORM} ${BUILD_DISTRO}

RUN apt-get update && \
    apt-get install -y curl pkg-config build-essential cmake git libssl-dev protobuf-compiler thrift-compiler && \
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | bash -s -- -y && \
    . $HOME/.cargo/env && \
    rustup default stable && \
    rustup target add aarch64-unknown-linux-gnu && \
    rustup component add rust-src

WORKDIR /work

ENTRYPOINT ["/bin/bash", "/work/src/backend/deployment/compilation/rust/compile.bash"]