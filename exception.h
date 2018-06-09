//
// Created by lion on 18-6-10.
//

#ifndef P_VECTOR_EXCEPTION_H
#define P_VECTOR_EXCEPTION_H

#include <stdexcept>

class archive_corrupted : public std::runtime_error {
public:
    explicit archive_corrupted() : runtime_error("archive corrupted") {};
};

class elf_corrupted : public std::runtime_error {
public:
    explicit elf_corrupted() : runtime_error("elf corrupted") {};
};

#endif //P_VECTOR_EXCEPTION_H
