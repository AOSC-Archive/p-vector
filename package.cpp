#include <thread>
#include <archive_entry.h>

#include "package.h"
#include "utils.h"
#include "elf_dependency.h"

static bool entry_is(archive_entry *e, const std::string &str) noexcept {
    return begins_with(archive_entry_pathname(e), str);
}

Package::Package() noexcept {
    this->deb = archive_read_new();
    archive_read_support_format_ar(this->deb);
    archive_read_support_filter_none(this->deb);
}

Package::~Package() noexcept {
    archive_read_free(this->deb);
}

void Package::scan(const std::string &path) {
    std::cout << "Scanning " << path << std::endl;

    if (archive_read_open_filename(this->deb, path.c_str(), 4096) != ARCHIVE_OK)
        throw archive_corrupted();
    archive_entry *e;
    while (archive_read_next_header(this->deb, &e) == ARCHIVE_OK) {

        if (entry_is(e, "control.tar"))
            this->control_tar();

        else if (entry_is(e, "data.tar"))
            this->data_tar();

    }
    if (archive_errno(this->deb) != ARCHIVE_OK) throw archive_corrupted();
}

void Package::control_tar() {
    int pipes[2];
    pipe(pipes);
    bool success = true;
    std::thread t([&] {
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
                    this->control = std::string(buffer, static_cast<unsigned long>(size));
                    this->mtime = archive_entry_mtime(e);
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
    int r = archive_read_data_into_fd(this->deb, pipes[1]);
    close(pipes[1]);
    t.join();
    if (!success || r != ARCHIVE_OK)
        throw archive_corrupted();
}

void Package::data_tar() {
    int pipes[2];
    pipe(pipes);
    bool success = true;
    std::thread t([&] {
        auto tar = archive_read_new();
        archive_read_support_format_tar(tar);
        archive_read_support_filter_all(tar);
        try {
            if (archive_read_open_fd(tar, pipes[0], 4096) != ARCHIVE_OK) throw archive_corrupted();
            archive_entry *e;
            while (archive_read_next_header(tar, &e) == ARCHIVE_OK) {
                this->data_tar_file(tar, e);
            }
            if (archive_errno(tar) != ARCHIVE_OK) throw archive_corrupted();
        } catch (archive_corrupted &except) {
            success = false;
        }
        close(pipes[0]);
        archive_read_free(tar);
    });
    int r = archive_read_data_into_fd(this->deb, pipes[1]);
    close(pipes[1]);
    t.join();
    if (!success || r != ARCHIVE_OK)
        throw archive_corrupted();
}

void Package::data_tar_file(archive *tar, archive_entry *e) {
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
    this->files.push_back(f);

    ElfDependency elf_dependency(
            [&](void *buf, size_t size) {
                la_int64_t ret = archive_read_data(tar, buf, size);
                if (ret < 0) throw archive_corrupted();
                return (size_t) ret;
            });

    try {
        elf_dependency.scan();
    } catch (elf_corrupted &e) {}

    if (begins_with(f.path, "./usr/lib"))
        this->so_provides.merge(elf_dependency.so_provides);

    this->so_depends.merge(elf_dependency.so_depends);
}