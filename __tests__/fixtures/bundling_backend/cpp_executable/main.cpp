#include <dlfcn.h>
#include <iostream>

int main(int argc, char** argv) {
    if (argc != 2) return 2;
    void* library = dlopen(argv[1], RTLD_NOW);
    if (!library) {
        std::cerr << dlerror() << '\n';
        return 3;
    }
    auto value = reinterpret_cast<int (*)()>(dlsym(library, "blitz_cpp_library_value"));
    if (!value) return 4;
    std::cout << value() + 1 << '\n';
    dlclose(library);
    return 0;
}
