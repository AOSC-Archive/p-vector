#ifndef P_VECTOR_PACKAGE_H
#define P_VECTOR_PACKAGE_H

#include <set>
#include <vector>
#include <string>
#include <stdexcept>
#include <archive.h>

#include "entry.h"

class archive_corrupted : public std::runtime_error {
public:
    explicit archive_corrupted() : runtime_error("archive corrupted") {};
};

class Package {
public:
    Package() noexcept;

    ~Package() noexcept;

    void scan(const std::string &path);

    std::string control;
    time_t mtime;
    std::vector<file_entry> files;
    std::set<std::string> so_provides;
    std::set<std::string> so_depends;

private:
    archive *deb;

    void control_tar();

    void data_tar();

    void data_tar_file(archive *tar, archive_entry *e);
};


#endif //P_VECTOR_PACKAGE_H
