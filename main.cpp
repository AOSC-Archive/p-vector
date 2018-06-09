#include <iostream>
#include <future>
#include <vector>
#include <set>

#include <archive.h>
#include <archive_entry.h>

#include "utils.h"
#include "exception.h"


struct file_entry {
    std::string path, name;
    bool is_dir;
    mode_t type;
    mode_t perm;
    la_int64_t uid, gid;
    std::string uname, gname;
};

struct package {
    std::string control;
    time_t mtime;
    std::vector<file_entry> files;
    std::set<std::string> so_provides;
    std::set<std::string> so_depends;
};

void process_control_tar(package &pkg, archive *a) {
    int pipes[2];
    pipe(pipes);
    bool success = true;
    std::thread t([&]() {
        auto tar = archive_read_new();
        archive_read_support_format_tar(tar);
        archive_read_support_filter_all(tar);
        const int MAX_BUFFER_SIZE = 1024 * 64;
        auto *buffer = new char[MAX_BUFFER_SIZE];
        try {
            if (archive_read_open_fd(tar, pipes[0], 4096) != ARCHIVE_OK) throw archive_corrupted();
            archive_entry *e;
            while (archive_read_next_header(tar, &e) == ARCHIVE_OK) {
                if (std::string(archive_entry_pathname(e)) == "./control" &&
                    archive_entry_filetype(e) == AE_IFREG) {
                    auto size = archive_read_data(tar, buffer, MAX_BUFFER_SIZE);
                    pkg.control = std::string(buffer, static_cast<unsigned long>(size));
                    pkg.mtime = archive_entry_mtime(e);
                }
            }
            if (archive_errno(tar) != ARCHIVE_OK) throw archive_corrupted();
        } catch (archive_corrupted &except) {
            success = false;
        }
        delete[] buffer;
        close(pipes[0]);
        archive_read_free(tar);
    });
    int r = archive_read_data_into_fd(a, pipes[1]);
    close(pipes[1]);
    t.join();
    if (!success || r != ARCHIVE_OK)
        throw archive_corrupted();
}

#include <elf.h>

bool test_elf_magic(archive *a) {
    char e_ident[EI_NIDENT];
    auto size = archive_read_data(a, e_ident, EI_NIDENT);
    if (size != EI_NIDENT) return false;
    return std::string(e_ident, SELFMAG) == ELFMAG;
}

std::pair<
        std::set<std::string>,
        std::set<std::string>
> scan_elf(archive *a) {
    // TODO: stub.
    return {{"a"}, {"b"}};
}

void process_data_tar_file(package &pkg, archive *a, archive_entry *e) {
    file_entry f = {
            .path = dirname(archive_entry_pathname(e)),
            .name = basename(archive_entry_pathname(e)),
            .is_dir = archive_entry_filetype(e) == AE_IFDIR,
            .type = archive_entry_filetype(e),
            .perm = archive_entry_perm(e),
            .uid = archive_entry_uid(e),
            .gid = archive_entry_gid(e),
            .uname = archive_entry_uname(e),
            .gname = archive_entry_gname(e),
    };
    pkg.files.push_back(f);
    if (f.type == AE_IFREG && test_elf_magic(a)) {
        try {
            auto so_info = scan_elf(a);
            pkg.so_provides.merge(so_info.first);
            pkg.so_depends.merge(so_info.second);
        } catch (elf_corrupted &except) {};
    }
}

void process_data_tar(package &pkg, archive *a) {
    std::cout << ">> data.tar" << std::endl;
    int pipes[2];
    pipe(pipes);
    bool success = true;
    std::thread t([&]() {
        auto tar = archive_read_new();
        archive_read_support_format_tar(tar);
        archive_read_support_filter_all(tar);
        try {
            if (archive_read_open_fd(tar, pipes[0], 4096) != ARCHIVE_OK) throw archive_corrupted();
            archive_entry *e;
            while (archive_read_next_header(tar, &e) == ARCHIVE_OK) {
                process_data_tar_file(pkg, tar, e);
            }
            if (archive_errno(tar) != ARCHIVE_OK) throw archive_corrupted();
        } catch (archive_corrupted &except) {
            success = false;
        }
        close(pipes[0]);
        archive_read_free(tar);
    });
    int r = archive_read_data_into_fd(a, pipes[1]);
    close(pipes[1]);
    t.join();
    if (!success || r != ARCHIVE_OK)
        throw archive_corrupted();
    std::cout << ">> data.tar done" << std::endl;
}

void deb_package(const std::string &path) {
    package pkg{};
    auto a = archive_read_new();
    archive_read_support_format_ar(a);
    archive_read_support_filter_none(a);
    try {
        if (archive_read_open_filename(a, path.c_str(), 4096) != ARCHIVE_OK)
            throw archive_corrupted();
        archive_entry *e;
        while (archive_read_next_header(a, &e) == ARCHIVE_OK) {
            if (entry_is(e, "control.tar")) {
                process_control_tar(pkg, a);
            } else if (entry_is(e, "data.tar")) {
                process_data_tar(pkg, a);
            }
        }
        if (archive_errno(a) != ARCHIVE_OK) throw archive_corrupted();
    } catch (archive_corrupted &except) {
        archive_read_free(a);
        throw;
    }
    archive_read_free(a);
}

int main() {
    try {
        deb_package("/home/lion/bash_4.4.12-0_amd64_debug.deb");
    } catch (archive_corrupted &except) {
        std::cerr << "archive is corrupted." << std::endl;
    }
}
