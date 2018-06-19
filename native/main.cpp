#include <iostream>
#include <iomanip>
#include <fcntl.h>
#include "main.h"
#include "package.h"

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

    // Serialize result into stdout with ProtoBuf
    Proto::pkg_info p{};
    p.set_size(pkg.size);
    p.set_hash_alg("SHA256");
    p.set_hash_value(pkg.sha256, sizeof(pkg.sha256));
    p.set_control(pkg.control);
    p.set_time(pkg.mtime);
    auto p_files = p.mutable_files();
    for (auto &i : pkg.files) {
        auto f = p_files->Add();
        f->set_path(i.path);
        f->set_is_dir(i.is_dir);
        f->set_size(i.size);
        f->set_type(i.type);
        f->set_perm(i.perm);
        f->set_uid(i.uid);
        f->set_gid(i.gid);
        f->set_uname(i.uname);
        f->set_gname(i.gname);
    }
    auto p_so_provides = p.mutable_so_provides(), p_so_depends = p.mutable_so_depends();
    for (auto &i : pkg.so_provides) *p_so_provides->Add() = i;
    for (auto &i : pkg.so_depends) *p_so_depends->Add() = i;
    p.SerializeToOstream(&std::cout);
}
