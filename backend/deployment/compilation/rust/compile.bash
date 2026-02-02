#!/bin/bash
set -e

source $HOME/.cargo/env
echo $MODULE_NAME
echo $PLATFORM_NAME
C_LIB_VERSION=$(ldd --version | head -n1 | awk '{print $NF}')
echo "C_LIB_VERSION: $C_LIB_VERSION"
cd /work

export CARGO_HOME=/work/target/$C_LIB_VERSION/$PLATFORM_NAME
mkdir -p $CARGO_HOME

export CARGO_TARGET_DIR=$CARGO_HOME
cargo build --release --bin $MODULE_NAME

RESULT_PATH=/work/build/release/$C_LIB_VERSION/$PLATFORM_NAME/rust/$MODULE_NAME
mkdir -p $RESULT_PATH

cp $CARGO_HOME/release/$MODULE_NAME $RESULT_PATH/$MODULE_NAME
ls -la $RESULT_PATH/$MODULE_NAME

echo "Done compiling $MODULE_NAME for $C_LIB_VERSION $PLATFORM_NAME finished!"