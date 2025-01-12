# Use Ubuntu base image compatible with ARM64 architecture
FROM ubuntu:22.04

# Set non-interactive mode for apt to avoid prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

RUN echo "Acquire::http::Pipeline-Depth 0;" > /etc/apt/apt.conf.d/99custom && \
    echo "Acquire::http::No-Cache true;" >> /etc/apt/apt.conf.d/99custom && \
    echo "Acquire::BrokenProxy    true;" >> /etc/apt/apt.conf.d/99custom

RUN apt-get update && apt-get upgrade -y \
    && apt-get install -y \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install essential development tools and dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    python3-pip \
    git \
    libeigen3-dev \
    libopencv-dev \
    libudev-dev \
    socatapt-get update && apt-get install -y \
    build-essential \
    cmake \
    python3-pip \
    git \
    libeigen3-dev \
    libopencv-dev \
    libudev-dev \
    socat && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Conan using pip
RUN pip3 install --upgrade pip && pip3 install conan

RUN conan profile detect

# Set the working directory
WORKDIR /mnt