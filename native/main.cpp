#include <iostream>
#include <fcntl.h>
#include "package.h"
#include "json.hpp"

int main(int argc, const char *argv[]) {
    int fd = 0;
    if (argc == 2) {
        fd = open(argv[1], O_CLOEXEC | O_RDONLY);
        if (fd < 0) return 1;
    }
    Package pkg{};
    try {
        pkg.scan(fd); // BOOM!
    } catch (archive_corrupted &except) {
        std::cerr << "archive is corrupted." << std::endl;
        return 2;
    }
    if (fd != 0) close(fd);

    using json = nlohmann::json;
    json j = {
            {"size",        pkg.size},
            {"hash_alg",    "SHA256"},
            {"hash_value",  pkg.sha256},
            {"control",     pkg.control},
            {"time",        pkg.mtime},
            {"so_provides", pkg.so_provides},
            {"so_depends",  pkg.so_depends},
    };
    auto j_files = json::array();
    for (auto &i : pkg.files) {
        json j_file = {
                {"path",   i.path},
                {"is_dir", i.is_dir},
                {"size",   i.size},
                {"type",   i.type},
                {"perm",   i.perm},
                {"uid",    i.uid},
                {"gid",    i.gid},
                {"uname",  i.uname},
                {"gname",  i.gname},
        };
        j_files.push_back(j_file);
    }
    j["files"] = j_files;
    std::cout << j.dump(-1, ' ', true) << std::endl;
    return 0;
}
