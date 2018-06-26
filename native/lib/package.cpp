#include <archive_entry.h>
#include <libgen.h>

#include "package.h"
#include "elf_dependency.h"
#include "package_archive_custom.h"


static bool begins_with(const std::string &str, const std::string &prefix) noexcept {
    return str.compare(0, prefix.size(), prefix) == 0;
}

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

void Package::scan(int fd) {
    if (my_archive_read_open_hash(this->deb, fd, this->sha256, &this->size) != ARCHIVE_OK)
        throw archive_corrupted();
    archive_entry *e;
    while (archive_read_next_header(this->deb, &e) == ARCHIVE_OK) {

        if (entry_is(e, "control.tar"))
            this->control_tar();

        else if (entry_is(e, "data.tar"))
            this->data_tar();

    }
    if (archive_errno(this->deb) != ARCHIVE_OK) throw archive_corrupted();
    archive_read_close(this->deb);
}

void Package::control_tar() {
    auto tar = archive_read_new();
    archive_read_support_format_tar(tar);
    archive_read_support_filter_all(tar);
    const int MAX_BUFFER_SIZE = 1024 * 64;
    auto *buffer = new char[MAX_BUFFER_SIZE];
    try {
        if (my_archive_read_open_nested(tar, this->deb) != ARCHIVE_OK)
            throw archive_corrupted();
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
        delete[] buffer;
        archive_read_free(tar);
        throw;
    }
    delete[] buffer;
    archive_read_free(tar);
}

void Package::data_tar() {
    auto tar = archive_read_new();
    archive_read_support_format_tar(tar);
    archive_read_support_filter_all(tar);
    try {
        if (my_archive_read_open_nested(tar, this->deb) != ARCHIVE_OK)
            throw archive_corrupted();
        archive_entry *e;
        while (archive_read_next_header(tar, &e) == ARCHIVE_OK) {
            this->data_tar_file(tar, e);
        }
        if (archive_errno(tar) != ARCHIVE_OK) throw archive_corrupted();
    } catch (archive_corrupted &except) {
        archive_read_free(tar);
        throw;
    }
    archive_read_free(tar);


    std::set<std::string> short_names{};
    for (auto &long_name : this->so_provides) {
        if (short_names.find(long_name) != short_names.end()) continue;
        for (auto &short_name : this->so_provides) {
            if (short_name == long_name) continue;
            if (begins_with(long_name + '.', short_name + '.')) {
                short_names.insert(short_name);
                break;
            }
        }
    }
    for (auto &short_name : short_names) {
        this->so_provides.erase(short_name);
    }

    std::vector<std::string> self_resolved{};
    for (auto &dep : this->so_depends) {
        if (this->so_priv_provides.find(dep) != this->so_priv_provides.end())
            self_resolved.push_back(dep);

        for (auto &prv : this->so_priv_provides) {
            if (begins_with(prv + '.', dep + '.')) {
                self_resolved.push_back(dep);
                break;
            }
        }
    }
    for (auto &dep : self_resolved) {
        this->so_depends.erase(dep);
    }

}

void Package::data_tar_file(archive *tar, archive_entry *e) {
    file_entry f = {
            .path = archive_entry_pathname(e),
            .size = archive_entry_size(e),
            .is_dir = archive_entry_filetype(e) == AE_IFDIR,
            .type = archive_entry_filetype(e),
            .perm = archive_entry_perm(e),
            .uid = archive_entry_uid(e),
            .gid = archive_entry_gid(e),
            .uname = archive_entry_uname(e),
            .gname = archive_entry_gname(e),
    };
    this->files.push_back(f);

    bool smells_like_so = (begins_with(f.path, "./usr/lib") && !begins_with(f.path, "./usr/libexec"))
                          || (begins_with(f.path, "./lib") && !begins_with(f.path, "./libexec"));

    bool looks_like_so = (f.path + ".").find(".so.") != std::string::npos;

    if (looks_like_so && smells_like_so && f.type == AE_IFLNK) {
        // Well... A symbolic link? Alright, I accept this one.
        this->so_provides.insert(basename((char *) f.path.c_str()));
        // A symbolic link is never an ELF.
        return;
    }

    ElfDependency elf_dependency(
            [&](void *buf, size_t size) {
                la_int64_t ret = archive_read_data(tar, buf, size);
                if (ret < 0) throw archive_corrupted();
                return (size_t) ret;
            });

    try {
        elf_dependency.scan();
        if (elf_dependency.is_dyn) {
            this->so_priv_provides.insert(elf_dependency.so_name);
            this->so_priv_provides.insert(basename((char *) f.path.c_str()));

            if (looks_like_so && smells_like_so) {
                this->so_provides.insert(elf_dependency.so_name);
                this->so_provides.insert(basename((char *) f.path.c_str()));
            }
        }
    } catch (elf_corrupted &e) {}

    this->so_depends.merge(elf_dependency.so_depends);
}