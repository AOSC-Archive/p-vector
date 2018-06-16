#include <iostream>

#include "package.h"

int main() {
    Package pkg;
    try {
        pkg.scan("/home/lion/PkgScan/bash_4.4.19-0_ppc64.deb");
    } catch (archive_corrupted &except) {
        std::cerr << "archive is corrupted." << std::endl;
    }
    std::cout << std::endl;

    std::cout << "PROVIDES: ";
    for (auto &item : pkg.so_provides)
        std::cout << item << ' ';
    std::cout << std::endl;

    std::cout << "DEPENDS: ";
    for (auto &item : pkg.so_depends)
        std::cout << item << ' ';
    std::cout << std::endl;

    std::cout << "FILES: " << pkg.files.size() << std::endl;

    std::cout << "MODIFY_TIME: " << pkg.mtime << std::endl;

    std::cout << std::endl << pkg.control;
}
