#!/bin/bash
set -e

echo $MODULE_NAME
echo $PLATFORM_NAME
echo $PROJECT_PATH
C_LIB_VERSION=$(ldd --version | head -n1 | awk '{print $NF}')
echo "C_LIB_VERSION: $C_LIB_VERSION"
cd /work/src/backend/$PROJECT_PATH

echo $BUILD_CMD
eval "$BUILD_CMD"

if [ -d "build" ]; then
    cd build
else
    echo "Warning: build directory does not exist, staying in current directory."
fi

ls -la

RESULT_PATH=/work/build/release/$C_LIB_VERSION/$PLATFORM_NAME/cpp/$MODULE_NAME

mkdir -p $RESULT_PATH

copy_files_with_symlinks() {
    local pattern="$1"
    find . -type f -name "$pattern" ! -path './.*' ! -path '*/CMakeFiles/*' | while read -r file; do
        target="$RESULT_PATH/$(basename "$file")"
        mkdir -p "$RESULT_PATH"
        cp "$file" "$target"
    done

    find . -type l -name "$pattern" ! -path './.*' ! -path '*/CMakeFiles/*' | while read -r file; do
        target="$RESULT_PATH/$(basename "$file")"
        mkdir -p "$RESULT_PATH"
        cp -P "$file" "$target"
    done
}

copy_files_with_symlinks "*.so"
copy_files_with_symlinks "*.so.*"
copy_files_with_symlinks "*.a"

find . -type f -perm -u=x ! -name "*.so" ! -name "*.so.*" ! -name "*.a" ! -name "*.o" ! -name "*.h" ! -name "*.cpp" ! -name "*.c" ! -name "*.txt" ! -name "*.md" ! -path './.*' ! -path '*/CMakeFiles/*' | while read -r file; do
    target="$RESULT_PATH/$(basename "$file")"
    mkdir -p "$RESULT_PATH"
    cp "$file" "$target"
done