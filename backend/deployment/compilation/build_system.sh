#!/usr/bin/env bash
# Execute the complete, ordered build graph for one discovered system.
set -Eeuo pipefail

report_failure() {
    local status="$?"
    printf '[blitz] FAILED phase=%s step=%s kind=%s module=%s exit=%s\n' \
        "${phase:-unknown}" "${step_id:-bootstrap}" "${kind:-bootstrap}" \
        "${module_name:-none}" "$status" >&2
    exit "$status"
}
trap report_failure ERR

prepare_python() {
    local binary="python${python_major}.${python_minor}"
    if command -v "$binary" >/dev/null 2>&1; then return; fi
    if [[ "$binary" != python3.12 ]]; then
        apt-get install -y "$binary" "${binary}-venv"
        return
    fi
    # Ubuntu 22.04 / JetPack 6 provides Python 3.10, while the installer
    # selects managed Python 3.12. Build the same ABI into the dependency
    # cache; the subsequent offline compilation phase never downloads it.
    apt-get install -y xz-utils zlib1g-dev libbz2-dev libreadline-dev \
        libsqlite3-dev libffi-dev liblzma-dev libncursesw5-dev uuid-dev
    local source_dir
    source_dir="$(mktemp -d)"
    curl --fail --location --retry 3 \
        https://www.python.org/ftp/python/3.12.6/Python-3.12.6.tar.xz \
        --output "$source_dir/python.tar.xz"
    echo "1999658298cf2fb837dffed8ff3c033ef0c98ef20cf73c5d5f66bed5ab89697c  $source_dir/python.tar.xz" | sha256sum --check
    tar -xJf "$source_dir/python.tar.xz" -C "$source_dir"
    (
        cd "$source_dir/Python-3.12.6"
        ./configure --prefix=/opt/blitz-python --with-ensurepip=install
        make -j "$(nproc)"
        make altinstall
    )
    rm -rf "$source_dir"
    "$binary" -c 'import ssl, bz2, sqlite3, lzma, ctypes, venv'
}

build_cpp_module() {
    local project_root="$1" module_name="$2" build_command="$3"
    local actual_glibc="$4" target_distro_key="$5"
    local release_path search_root file destination
    cd "$project_root"
    export CPP_BUILD_DIR="build/$actual_glibc/$target_distro_key"
    bash -c "$build_command"
    release_path="$project_root/$CPP_BUILD_DIR/release"
    search_root="$project_root/$CPP_BUILD_DIR"
    if [[ ! -d "$search_root" ]]; then
        echo "C++ build output missing: $search_root" >&2
        return 1
    fi
    mkdir -p "$release_path" "/artifacts/cpp/$module_name"
    while IFS= read -r -d '' file; do
        destination="$release_path/$(basename "$file")"
        if [[ -e "$destination" ]] && ! cmp -s "$file" "$destination"; then
            echo "Conflicting C++ output basename: $file and $destination. Export distinct release paths." >&2
            return 1
        fi
        cp -a "$file" "$release_path/"
    done < <(find "$search_root" \( -type f -o -type l \) \( -name '*.so' -o -name '*.so.*' -o -name '*.a' -o -name '*.dylib' -o -name '*.dll' -o -name '*.lib' -o -perm -u=x \) ! -path "$release_path/*" ! -path '*/CMakeFiles/*' -print0)
    cp -a "$release_path/." "/artifacts/cpp/$module_name/"
}

build_rust_module() {
    local project_root="$1" module_name="$2" binary_name="$3"
    local manifest_dir="$project_root"
    export CARGO_TARGET_DIR="/work/cargo-target/$module_name"
    while [[ ! -f "$manifest_dir/Cargo.toml" && "$manifest_dir" != /work ]]; do
        manifest_dir="$(dirname "$manifest_dir")"
    done
    if [[ ! -f "$manifest_dir/Cargo.toml" ]]; then
        echo "Cargo.toml not found for $module_name" >&2
        return 1
    fi
    mkdir -p "/artifacts/rust/$module_name"
    if [[ -n "$binary_name" ]]; then
        cargo build --offline --release --manifest-path "$manifest_dir/Cargo.toml" --bin "$binary_name"
        cp "$CARGO_TARGET_DIR/release/$binary_name" "/artifacts/rust/$module_name/"
    else
        cargo build --offline --release --manifest-path "$manifest_dir/Cargo.toml" --lib
        local library_count=0 library
        for library in "$CARGO_TARGET_DIR"/release/*.so "$CARGO_TARGET_DIR"/release/*.a "$CARGO_TARGET_DIR"/release/*.rlib; do
            if [[ -f "$library" ]]; then
                cp "$library" "/artifacts/rust/$module_name/"
                library_count=$((library_count + 1))
            fi
        done
        if [[ "$library_count" -eq 0 ]]; then
            echo "Rust library output missing for $module_name in $CARGO_TARGET_DIR/release" >&2
            return 1
        fi
    fi
}


phase="${1:-all}"
if [[ "$phase" != provision && "$phase" != compile && "$phase" != all ]]; then
    echo "Unknown build phase: $phase" >&2
    exit 1
fi
export DEBIAN_FRONTEND=noninteractive TZ=UTC
export PATH="/opt/blitz-python/bin:$PATH"
step_id=bootstrap-packages kind=bootstrap module_name=none
printf '[blitz] START phase=%s step=%s\n' "$phase" "$step_id"
if [[ "$phase" != compile ]]; then
    apt-get update
    apt-get install -y jq ca-certificates
fi
printf '[blitz] DONE phase=%s step=%s\n' "$phase" "$step_id"

if [[ "$phase" == provision ]]; then
    plan="${BLITZ_PLAN_PATH:-/work/provision-plan.json}"
else
    plan="${BLITZ_PLAN_PATH:-/work/build-plan.json}"
fi
target_glibc="$(jq -r '.system.glibc' "$plan")"
actual_glibc="$(ldd --version | awk 'NR == 1 { print $NF }')"
if [[ "$actual_glibc" != "$target_glibc" ]]; then
    echo "[blitz] FAILED phase=$phase step=validate-system: build image glibc $actual_glibc differs from target $target_glibc" >&2
    exit 1
fi
target_distro_key="$(jq -r '.system.distro_key' "$plan")"
python_major="$(jq -r '.system.python_major' "$plan")"
python_minor="$(jq -r '.system.python_minor' "$plan")"
build_python="$(command -v "python${python_major}.${python_minor}" || true)"
build_python="${build_python:-python3}"
if [[ "$phase" != provision ]]; then
    mkdir -p /artifacts
fi

while IFS= read -r step; do
    step_id="$(jq -r '.id' <<< "$step")"
    kind="$(jq -r '.kind' <<< "$step")"
    module_name="$(jq -r '.module // empty' <<< "$step")"
    source_path="$(jq -r '.source // empty' <<< "$step")"
    case "$phase:$kind" in
        compile:system-packages|compile:cpp-dependencies|compile:rust-toolchain|compile:rust-fetch|compile:python-wheels|\
        provision:cpp-build|provision:rust-build|provision:native-libraries|provision:copy-module|provision:shared-generated)
            continue ;;
    esac
    printf '[blitz] START phase=%s step=%s kind=%s module=%s\n' \
        "$phase" "$step_id" "$kind" "${module_name:-none}"
    if [[ "$phase" != provision && "$kind" != native-libraries && "$kind" != shared-generated ]]; then
        build_environment="$("$build_python" /work/build_artifacts.py build-environment "$step")"
        dependency_paths="$(jq -r '.libraries' <<< "$build_environment")"
        header_paths="$(jq -r '.headers' <<< "$build_environment")"
        export BLITZ_LIB_DIR=/artifacts/lib BLITZ_INCLUDE_DIR=/artifacts/include
        export BLITZ_RESOURCE_DIR="/artifacts/resources/$module_name"
        export BLITZ_GENERATED_DIR=/artifacts/shared/backend/generated
        export LIBRARY_PATH="$dependency_paths" LD_LIBRARY_PATH="$dependency_paths"
        export CPATH="$header_paths" CMAKE_PREFIX_PATH="${header_paths//:/;}"
        export CMAKE_LIBRARY_PATH="$dependency_paths" CMAKE_INCLUDE_PATH="$header_paths"
        export RUSTFLAGS="${dependency_paths:+-L native=${dependency_paths//:/ -L native=}}"
    fi
    case "$kind" in
        shared-generated)
            mkdir -p /artifacts/shared/backend
            cp -a "$source_path/." /artifacts/shared/backend/
            ;;
        system-packages)
            if [[ "$phase" == compile ]]; then continue; fi
            apt-get install -y curl git build-essential cmake pkg-config libssl-dev python3 python3-venv python3-pip file
            prepare_python
            build_python="$(command -v "python${python_major}.${python_minor}")"
            ;;
        cpp-dependencies)
            if [[ "$phase" == compile ]]; then continue; fi
            libraries="$(jq -r '.libraries // empty' <<< "$step")"
            extra_commands="$(jq -r '.extra_commands // empty' <<< "$step")"
            if [[ -n "$libraries" ]]; then bash -c "$libraries"; fi
            if [[ -n "$extra_commands" ]]; then bash -c "$extra_commands"; fi
            ;;
        rust-toolchain)
            if [[ "$phase" == compile ]]; then continue; fi
            apt-get install -y protobuf-compiler thrift-compiler
            curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal
            source "$HOME/.cargo/env"
            ;;
        rust-fetch)
            if [[ "$phase" == compile ]]; then continue; fi
            source "$HOME/.cargo/env"
            cargo fetch --manifest-path "$source_path/Cargo.toml"
            ;;
        cpp-build)
            if [[ "$phase" == provision ]]; then continue; fi
            "$build_python" /work/build_artifacts.py validate-toolkit "$step" "$plan"
            command="$(jq -r '.command' <<< "$step")"
            build_cpp_module "$source_path" "$module_name" "$command" "$actual_glibc" "$target_distro_key"
            ;;
        rust-build)
            if [[ "$phase" == provision ]]; then continue; fi
            "$build_python" /work/build_artifacts.py validate-toolkit "$step" "$plan"
            source "$HOME/.cargo/env"
            binary="$(jq -r '.binary // empty' <<< "$step")"
            build_rust_module "$source_path" "$module_name" "$binary"
            ;;
        native-libraries)
            if [[ "$phase" == provision ]]; then continue; fi
            "$build_python" /work/build_artifacts.py finalize "$plan"
            ;;
        copy-module)
            if [[ "$phase" == provision ]]; then continue; fi
            language="$(jq -r '.language' <<< "$step")"
            mkdir -p "/artifacts/$language/$module_name"
            cp -a "$source_path/." "/artifacts/$language/$module_name/"
            ;;
        python-wheels)
            if [[ "$phase" == compile ]]; then continue; fi
            python_binary="python${python_major}.${python_minor}"
            "$python_binary" -m venv /tmp/blitz-wheel-venv
            mkdir -p /artifacts/deps/python
            cd /work/dependency-inputs/python
            /tmp/blitz-wheel-venv/bin/python -m pip wheel --wheel-dir /artifacts/deps/python --requirement requirements.txt
            cp -a /work/dependency-inputs/python/. /artifacts/deps/python/
            ;;
        *) echo "Unknown build step: $kind" >&2; exit 1 ;;
    esac
    case "$kind" in
        cpp-build|rust-build|copy-module)
            "$build_python" /work/build_artifacts.py export "$step" ;;
    esac
    printf '[blitz] DONE phase=%s step=%s\n' "$phase" "$step_id"
done < <(jq -c '.steps[]' "$plan")
