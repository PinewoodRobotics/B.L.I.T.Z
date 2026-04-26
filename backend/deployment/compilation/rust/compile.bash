#!/bin/bash
set -e

source $HOME/.cargo/env
C_LIB_VERSION=$(ldd --version | head -n1 | awk '{print $NF}')
cd /work

export CARGO_HOME=/work/target/$C_LIB_VERSION/$LINUX_DISTRO
mkdir -p $CARGO_HOME

export CARGO_TARGET_DIR=$CARGO_HOME
cargo build --release --bin $MODULE_NAME

RESULT_PATH=$CARGO_HOME/release/
# RESULT_PATH=/work/build/release/rust/$C_LIB_VERSION/$LINUX_DISTRO/$MODULE_NAME
# mkdir -p $RESULT_PATH

# cp $CARGO_HOME/release/$MODULE_NAME $RESULT_PATH/$MODULE_NAME

echo "LINUX_DISTRO=$LINUX_DISTRO"
echo "C_LIB_VERSION=$C_LIB_VERSION"
echo "RESULT_PATH=${RESULT_PATH#/work/}"