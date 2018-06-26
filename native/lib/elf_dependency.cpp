#include <elf.h>
#include <iostream>

#include "elf_dependency.h"

ElfDependency::ElfDependency(std::function<size_t(void *, size_t)> read) {
    this->read = std::move(read);
}

const size_t DISCARD_BLOCK_SIZE = 1024;
char discard_buf[DISCARD_BLOCK_SIZE];

void ElfDependency::must_seek(size_t target) {
    if (target < buffer.size()) {
        current = target;
        return;
    }
    current = buffer.size();
    size_t distance = target - current;
    size_t blocks = distance / DISCARD_BLOCK_SIZE;
    size_t tail = distance % DISCARD_BLOCK_SIZE;
    for (unsigned i = 0; i < blocks; ++i) {
        must_read(discard_buf, DISCARD_BLOCK_SIZE);
    }
    if (tail) must_read(discard_buf, tail);
}

void ElfDependency::must_read(void *buf, size_t size) {
    if (current == buffer.size()) {
        size_t size_read = this->read(buf, size);
        buffer.append((char *) buf, size_read);
        current += size_read;
        if (size_read != size) throw elf_corrupted();
    } else if (current + size <= buffer.size()) {
        buffer.copy((char *) buf, size, current);
        current += size;
    } else if (current < buffer.size()) {
        auto cached_size = buffer.size() - current;
        must_read(buf, cached_size);
        must_read((char *) buf + cached_size, size - cached_size);
    } else {
        return;
    }
}

std::string ElfDependency::lookup_table(size_t ptr) {
    if (ptr >= dyn_str_table.size()) throw elf_corrupted();
    auto end = dyn_str_table.find((char) '\0', ptr);
    if (end == std::string::npos) {
        return dyn_str_table.substr(ptr, end);
    }
    return dyn_str_table.substr(ptr, end - ptr);
}

void ElfDependency::scan() {
    unsigned char e_ident[EI_NIDENT];
    must_read(e_ident, sizeof(e_ident));
    if (std::string((char *) e_ident, SELFMAG) != ELFMAG) throw elf_corrupted();

    endian = e_ident[EI_DATA];

    if (e_ident[EI_CLASS] == ELFCLASS32)
        scan<Elf32_Ehdr, Elf32_Shdr, Elf32_Dyn>();
    else if (e_ident[EI_CLASS] == ELFCLASS64)
        scan<Elf64_Ehdr, Elf64_Shdr, Elf64_Dyn>();
    else throw elf_corrupted();
}

template<class _Ehdr, class _Shdr, class _Dyn>
void ElfDependency::scan() {
    // Get Ehdr
    _Ehdr ehdr{};
    must_read((char *) &ehdr + EI_NIDENT, sizeof(ehdr) - EI_NIDENT);
    is_dyn = ehdr.e_type == ET_DYN;

    // Get Shdr
    must_seek(H(ehdr.e_shoff));
    std::vector<_Shdr> shdr_array;
    int dyn_idx = -1, dyn_str_idx = -1;
    for (int i = 0; i < H(ehdr.e_shnum); ++i) {
        _Shdr shdr{};
        must_read(&shdr, sizeof(shdr));
        shdr_array.push_back(shdr);
        // Find dynamic section
        if (H(shdr.sh_type) == SHT_DYNAMIC) {
            dyn_idx = i;
            dyn_str_idx = H(shdr.sh_link);
            if (dyn_str_idx > H(ehdr.e_shnum) - 1) throw elf_corrupted();
        }
    }

    if (dyn_idx == -1) return;

    std::vector<_Dyn> dyn_array;
    { // Read dynamic section entries
        auto table_offset = H(shdr_array[dyn_idx].sh_offset);
        auto table_size = H(shdr_array[dyn_idx].sh_size);
        must_seek(table_offset);
        while (current < table_offset + table_size) {
            _Dyn dyn{};
            must_read(&dyn, sizeof(dyn));
            dyn_array.push_back(dyn);
        }
    }

    { // Read string table section
        auto table_offset = H(shdr_array[dyn_str_idx].sh_offset);
        auto table_size = H(shdr_array[dyn_str_idx].sh_size);
        must_seek(table_offset);
        auto *str_table = new char[table_size];
        try {
            must_read(str_table, table_size);
        } catch (...) {
            delete[] str_table;
            throw;
        }
        dyn_str_table = std::string(str_table, table_size);
        delete[] str_table;
    }

    for (auto &dyn : dyn_array) {
        if (H(dyn.d_tag) == DT_NEEDED) {
            so_depends.insert({lookup_table(H(dyn.d_un.d_val))});
        } else if (H(dyn.d_tag) == DT_SONAME) {
            so_name = lookup_table(H(dyn.d_un.d_val));
        }
    }
}

template<class T>
T ElfDependency::H(T v) noexcept {
    if (endian == ELFDATA2MSB) {
        switch (sizeof(T)) {
            case 1:
                return v;
            case 2:
                return be16toh(v);
            case 4:
                return be32toh(v);
            case 8:
                return be64toh(v);
            default:
                std::cerr << "malformed type" << std::endl;
                exit(1);
        }
    } else {
        switch (sizeof(T)) {
            case 1:
                return v;
            case 2:
                return le16toh(v);
            case 4:
                return le32toh(v);
            case 8:
                return le64toh(v);
            default:
                std::cerr << "malformed type" << std::endl;
                exit(1);
        }
    }
}
