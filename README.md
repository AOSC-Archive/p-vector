# p-vector
<!--
Maintain your own .deb repository now!
Scanning packages, generating `Packages`, `Contents-*` and `Release`, all in one.

Multi repository, finding potential file collisions, checking shared object compatibilities and more integrity checking features is coming.
-->

## Dependencies
- Python 3
- OpenSSL (libcrypto) (`libssl-dev` in Debian 10)
- LibArchive (`libarchive-dev` in Debian 10)
- (Python 3) psycopg2, zmq, requests

And you need a PostgreSQL server. You may deploy one on your local machine.

Compile-time:
- CMake
- G++ (support C++17 or later)
