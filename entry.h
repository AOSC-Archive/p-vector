//
// Created by lion on 18-6-13.
//

#ifndef P_VECTOR_P_VECTOR_H
#define P_VECTOR_P_VECTOR_H

#include <set>
#include <vector>
#include <string>

struct file_entry {
    std::string path, name;
    bool is_dir;
    mode_t type;
    mode_t perm;
    int64_t uid, gid;
    std::string uname, gname;
};

#endif //P_VECTOR_P_VECTOR_H
