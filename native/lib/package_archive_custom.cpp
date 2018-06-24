#include <cerrno>

#include <archive.h>
#include <archive_entry.h>
#include <openssl/sha.h>


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

int my_archive_read_open_nested(archive *a, archive *parent) {
    return archive_read_open(a, parent, dummy_cb, read_pipe_cb, dummy_cb);
}


struct payload_hash_fd {
    int _fd;
    off_t *size;
    SHA256_CTX *_ctx;
    unsigned char *_buf;
    unsigned char *result;
};

static int close_hash_fd_cb(struct archive *, void *_client_data) {
    auto p = (payload_hash_fd *) _client_data;
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
            SHA256_Update(p->_ctx, p->_buf, (size_t) size);
            *p->size += size;
        }
        return size;
    }
}

int my_archive_read_open_hash(archive *a, int fd, unsigned char *result, off_t *file_size) {
    auto ctx = new SHA256_CTX;
    SHA256_Init(ctx);
    auto p = new payload_hash_fd{fd, file_size, ctx, new unsigned char[4096], result};
    return archive_read_open(a, p, dummy_cb, read_hash_fd_cb, close_hash_fd_cb);
}
