# p-vector
<!--
Maintain your own .deb repository now!
Scanning packages, generating `Packages`, `Contents-*` and `Release`, all in one.

Multi repository, finding potential file collisions, checking shared object compatibilities and more integrity checking features is coming.
-->

## Dependencies
- Python 3
- OpenSSL (libcrypto)
- LibArchive
- (Python 3) psycopg2

And you need a PostgreSQL server. You may deploy one on your local machine.

Compile-time:
- CMake
- G++ (support C++17 or later)
