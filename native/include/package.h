#ifndef P_VECTOR_PACKAGE_H
#define P_VECTOR_PACKAGE_H

#include <set>
#include <vector>
#include <string>
#include <stdexcept>
#include <archive.h>
#include <openssl/sha.h>
#include <cstdint>
#include <ctime>

class archive_corrupted : public std::runtime_error {
public:
    explicit archive_corrupted() : runtime_error("archive corrupted") {};
};

struct file_entry {
    std::string path;
    off_t size;
    bool is_dir;
    mode_t type;
    mode_t perm;
    std::int64_t uid, gid;
    std::string uname, gname;
};

class Package {
public:
    Package() noexcept;

    ~Package() noexcept;

    void scan(int fd);

    std::string control{};
    std::time_t mtime{};
    std::vector<file_entry> files{};
    std::set<std::string> so_provides{};
    std::set<std::string> so_depends{};
    off_t size{};
    unsigned char sha256[SHA256_DIGEST_LENGTH]{};

private:
    archive *deb;

    void control_tar();

    void data_tar();

    void data_tar_file(archive *tar, archive_entry *e);
};


#endif //P_VECTOR_PACKAGE_H
