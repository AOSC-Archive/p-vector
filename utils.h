//
// Created by lion on 18-6-9.
//

#ifndef P_VECTOR_UTILS_H
#define P_VECTOR_UTILS_H

#include <iostream>

#include <archive.h>
#include <archive_entry.h>

bool entry_is(archive_entry *e, const std::string &str) noexcept {
    std::string filename = archive_entry_pathname(e);
    return filename.compare(0, str.size(), str) == 0;
}

void _archive_print_error(archive *a, const char *file, int line) {
    std::cerr << file << ':' << line << ' ' << archive_errno(a) << ' ' << archive_error_string(a) << std::endl;
}

#define archive_print_error(a) _archive_print_error(a, __FILE__, __LINE__)

std::string basename(const std::string& path) {
    return std::string(path, path.find_last_of('/')+1);
}

std::string dirname(const std::string& path) {
    return std::string(path, 0, path.find_last_of('/')+1);
}

#endif //P_VECTOR_UTILS_H
