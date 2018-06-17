#include <iostream>
#include <iomanip>

#include "package.h"

int main() {
    Package pkg{};
    try {
        pkg.scan("/home/lion/PkgScan/bash_4.4.19-0_ppc64.deb");
    } catch (archive_corrupted &except) {
        std::cerr << "archive is corrupted." << std::endl;
    }
    std::cout << std::endl;

    std::cout << "PROVIDES: ";
    for (auto &i : pkg.so_provides)
        std::cout << i << ' ';
    std::cout << std::endl;

    std::cout << "DEPENDS: ";
    for (auto &i : pkg.so_depends)
        std::cout << i << ' ';
    std::cout << std::endl;

    std::cout << "FILES: " << pkg.files.size() << std::endl;

    std::cout << "MODIFY_TIME: " << pkg.mtime << std::endl;

    std::cout << std::endl << pkg.control;

    std::cout << "Size: " << pkg.size << std::endl;
    std::cout << "SHA256: ";
    for (auto i : pkg.sha256)
        std::cout << std::setfill('0') << std::setw(2) << std::hex << (int) i;
    std::cout << std::endl;
}
