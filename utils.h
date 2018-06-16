#ifndef P_VECTOR_UTILS_H
#define P_VECTOR_UTILS_H

#include <iostream>

static std::string basename(const std::string &path) noexcept {
    return std::string(path, path.find_last_of('/') + 1);
}

static std::string dirname(const std::string &path) noexcept {
    return std::string(path, 0, path.find_last_of('/') + 1);
}

static bool begins_with(const std::string &str, const std::string &prefix) noexcept {
    return str.compare(0, prefix.size(), prefix) == 0;
}

#endif //P_VECTOR_UTILS_H
