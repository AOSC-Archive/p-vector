#ifndef P_VECTOR_ELF_DEPENDENCY_H
#define P_VECTOR_ELF_DEPENDENCY_H

#include <stdexcept>
#include <functional>
#include <set>
#include <string>

class elf_corrupted : public std::runtime_error {
public:
    explicit elf_corrupted() : runtime_error("elf corrupted") {};
};

class ElfDependency {
public:
    explicit ElfDependency(std::function<size_t(void *, size_t)>);

    void scan();

    std::set<std::string> so_provides;
    std::set<std::string> so_depends;

private:
    template<class _Ehdr, class _Shdr, class _Dyn>
    void scan();

    template<class T>
    T H(T v) noexcept;

    void must_read(void *, size_t);

    void must_seek(size_t);

    std::string lookup_table(size_t);

    std::function<size_t(void *, size_t)> read;
    size_t current = 0;
    std::string buffer;
    std::string dyn_str_table;
    unsigned char endian;
};

#endif //P_VECTOR_ELF_DEPENDENCY_H
