#ifndef P_VECTOR_PACKAGE_ARCHIVE_CUSTOM_H
#define P_VECTOR_PACKAGE_ARCHIVE_CUSTOM_H

#include <archive.h>

int my_archive_read_open_nested(archive *a, archive *parent);

int my_archive_read_open_hash(archive *a, int fd, unsigned char *result, off_t *file_size);

#endif //P_VECTOR_PACKAGE_ARCHIVE_CUSTOM_H
