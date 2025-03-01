conan install . --build=missing -of=build
cd build
cmake .. -DCMAKE_TOOLCHAIN_FILE=../build/conan_toolchain.cmake -DCMAKE_BUILD_TYPE=Release