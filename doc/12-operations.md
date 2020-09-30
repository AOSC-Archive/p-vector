### Operations

`p-vector` supports the following operation:

*`scan`*
:   Scans the pool directory for updated packages.
:   Branches and pool location is specified in the configuration YAML. See **[CONFIGURATION](#configuration)** for YAML format. `p-vector` populates information in the database with metadata of newly added or updated `deb` packages on disk. Note that `scan` is not responsible for APT repository asset generation. This operation accepts no options.

*`release [--force]`*
:   Generates APT repository assets, and applies PGP signature.
:   APT assets include `InRelease` for each branch, `Contents-$ARCH`, `Pacakges` and `Packages.xz` for each branch-component-architecture combination and their PGP-signed parts.
:   Data used for asset generation are obtained from the database, not the `deb` packages. If data for a certain branch-component-architecture combination has not been updated on the database since the last time APT assets were generated, `p-vector` will not regenerate assets for that branch-component-architecture combination to reduce write traffic to disk. However, the *`--force`* option will cause `p-vector` to regenerate and re-sign assets.

*`sync`*
:   Synchronizes main repository data to local database from AOSC servers.
:   The data aid the dependency analyzer to find potential packaging quality issues or breakage. This is not required for creating and publishing a working APT repository.

*`analyze`*
:   Analyzes potential issues for the current repository and stores them in the database. In addition to directly querying the database, a set of utilities can be used to build a web frontend to the database. See [AOSC Wiki Page on the Packages Site](https://wiki.aosc.io/developer/infrastructure/packages-site/) for more information. An official instance to query main AOSC repository is currently hosted at <https://packages.aosc.io>.

*`reset table_category`*
:   Drops data from the database.
:   **WARNING: This operation may render `p-vector` inoperable if used incorrectly.**

:   For `table_category`, pass *`pv`* to drop all state information and package metadata related to local repositories. Pass *`sync`* to drop main repository data obtained from AOSC servers. Pass *`all`* to delete both.
