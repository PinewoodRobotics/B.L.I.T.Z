FROM --platform=linux/arm64 ubuntu:22.04

# Prevent prompts during install
ENV DEBIAN_FRONTEND=noninteractive

# Update + install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    ninja-build \
    clang \
    gdb \
    lldb \
    lcov \
    valgrind \
    pkg-config \
    libssl-dev \
    libclang-dev \
    curl \
    git \
    unzip \
    zip \
    wget \
    software-properties-common \
    ca-certificates \
    python3 \
    python3-dev \
    python3-pip \
    python3-venv \
    python3-setuptools \
    python3-wheel \
    python-is-python3 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

ENV PATH="/root/.cargo/bin:${PATH}"

RUN rustc --version && cargo --version && python3 --version && g++ --version

RUN rustup update

CMD [ "bash" ]

WORKDIR /mnt