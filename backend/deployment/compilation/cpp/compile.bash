#!/bin/bash
set -e

C_LIB_VERSION=$(ldd --version | head -n1 | awk '{print $NF}')
PROJECT_ROOT="/work/$PROJECT_PATH"
cd "$PROJECT_ROOT"

export CPP_BUILD_DIR="build/$C_LIB_VERSION/$LINUX_DISTRO"
RESULT_PATH="$PROJECT_ROOT/$CPP_BUILD_DIR/release"

echo $BUILD_CMD
eval "$BUILD_CMD"

if [ -d "$PROJECT_ROOT/$CPP_BUILD_DIR" ]; then
    cd "$PROJECT_ROOT/$CPP_BUILD_DIR"
else
    echo "Warning: build directory $CPP_BUILD_DIR does not exist, staying in current directory."
fi

ls -la

mkdir -p $RESULT_PATH

copy_files_with_symlinks() {
    local pattern="$1"
    find . -type f -name "$pattern" ! -path './.*' ! -path './release/*' ! -path '*/CMakeFiles/*' | while read -r file; do
        target="$RESULT_PATH/$(basename "$file")"
        mkdir -p "$RESULT_PATH"
        cp "$file" "$target"
    done

    find . -type l -name "$pattern" ! -path './.*' ! -path './release/*' ! -path '*/CMakeFiles/*' | while read -r file; do
        target="$RESULT_PATH/$(basename "$file")"
        mkdir -p "$RESULT_PATH"
        cp -P "$file" "$target"
    done
}

copy_files_with_symlinks "*.so"
copy_files_with_symlinks "*.so.*"
copy_files_with_symlinks "*.a"
copy_files_with_symlinks "*.dylib"
copy_files_with_symlinks "*.dll"
copy_files_with_symlinks "*.lib"

find . -type f -perm -u=x ! -name "*.so" ! -name "*.so.*" ! -name "*.a" ! -name "*.o" ! -name "*.h" ! -name "*.cpp" ! -name "*.c" ! -name "*.txt" ! -name "*.md" ! -path './.*' ! -path './release/*' ! -path '*/CMakeFiles/*' | while read -r file; do
    target="$RESULT_PATH/$(basename "$file")"
    mkdir -p "$RESULT_PATH"
    cp "$file" "$target"
done

echo "LINUX_DISTRO=$LINUX_DISTRO"
echo "C_LIB_VERSION=$C_LIB_VERSION"
echo "RESULT_PATH=${RESULT_PATH#/work/}"