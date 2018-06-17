#include <thread>
#include <archive_entry.h>
#include <openssl/sha.h>
#include <fcntl.h>

#include "package.h"
#include "utils.h"
#include "elf_dependency.h"

static bool entry_is(archive_entry *e, const std::string &str) noexcept {
    return begins_with(archive_entry_pathname(e), str);
}

static int dummy_cb(struct archive *, void *) {
    return ARCHIVE_OK;
}

static la_ssize_t read_pipe_cb(struct archive *a, void *_client_data, const void **_buffer) {
    size_t size;
    la_int64_t offset;
    archive_read_data_block((archive *) _client_data, _buffer, &size, &offset);
    archive_copy_error((archive *) _client_data, a);
    return size;
}

int archive_read_open_nested(archive *a, archive *parent) {
    return archive_read_open(a, parent, dummy_cb, read_pipe_cb, dummy_cb);
}

struct payload_hash_fd {
    int _fd;
    SHA256_CTX *_ctx;
    unsigned char *_buf;
    unsigned char *result;
};

static int close_hash_fd_cb(struct archive *, void *_client_data) {
    auto p = (payload_hash_fd *) _client_data;
    close(p->_fd);
    SHA256_Final(p->result, p->_ctx);
    delete p->_ctx;
    delete[] p->_buf;
    delete p;
    return ARCHIVE_OK;
}

static la_ssize_t read_hash_fd_cb(struct archive *a, void *_client_data, const void **_buffer) {
    auto p = (payload_hash_fd *) _client_data;
    *_buffer = p->_buf;

    while (true) {
        ssize_t size = read(p->_fd, p->_buf, 4096);
        if (size < 0) {
            if (errno == EINTR) continue;
            archive_set_error(a, errno, "failed to read() on fd");
        } else {
            SHA256_Update(p->_ctx, p->_buf, size);
        }
        return size;
    }
}

int archive_read_open_hash(archive *a, const std::string &path, unsigned char *result) {
    int fd = open(path.c_str(), O_CLOEXEC | O_RDONLY);
    if (fd < 0) return ARCHIVE_FAILED;
    auto ctx = new SHA256_CTX;
    SHA256_Init(ctx);
    auto p = new payload_hash_fd{fd, ctx, new unsigned char[4096], result};
    return archive_read_open(a, p, dummy_cb, read_hash_fd_cb, close_hash_fd_cb);
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

    struct stat st{};
    if (stat(path.c_str(), &st) < 0) throw archive_corrupted();
    this->size = st.st_size;

    if (archive_read_open_hash(this->deb, path, this->sha256) != ARCHIVE_OK)
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
        if (archive_read_open_nested(tar, this->deb) != ARCHIVE_OK)
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
        if (archive_read_open_nested(tar, this->deb) != ARCHIVE_OK)
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