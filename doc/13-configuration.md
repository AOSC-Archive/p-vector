# Configuration

A single `p-vector` instance manages exactly one APT pool and one dist directory. A `p-vector` instance operates off of a configuration YAML and a PostgreSQL database.

### PostgreSQL

You will need a PostgreSQL database for `p-vector` to retain its state information about managed APT repository and packages. Assuming `p-vector` is installed at `/usr/bin/p-vector`, run the following in your shell to bootstrap a database for use with `p-vector`:

```{caption="Bootstrapping database"}
psql $DB_NAME < /usr/libexec/p-vector/abbsdb.sql
psql $DB_NAME < /usr/libexec/p-vector/vercomp.sql
```

### YAML

The YAML _file_ should contain at least one or more YAML _sections_, with the first YAML section containing global parameters. For instance:

```{caption="Configuration file: Global section"}
db_pgconn: dbname=db_pv
path: /build/output
zmq_change: ipc:///run/p-v/zmq
populate: true
origin: jelly.aosc.io
label: A cool repo of cooked jelly
codename: jelly-cooking
ttl: 10
renew_in: 2
desc: "Cooked Jelly for %BRANCH%"
---
 ... branch specific parameters ...
---
 ... branch specific parameters ...
```

Here below we explain the global parameters that affects `p-vector` itself:

*`db_pgconn`*
:   Accepts a set of connection parameters in the form of a PostgreSQL connection string[^connstring]. This specifies the PostgreSQL database in which `p-vector` stores package metadata. The database must exist and the invoking user must have read-write permission to that database. For local usage, a single _`dbname=foo`_ should be enough.

[^connstring]: See [PostgreSQL Documentation](https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING) on how to reference a database connection.

*`path`*
:   Accepts a path where `p-vector` will search for `deb` packages and place generated APT assets. See the **[REPOSITORY STRUCTURE](#repository-structure)** section for details.

*`populate`*
:   Accepts a boolean value. This parameter controls whether `p-vector` should implicitly treat all directories under `$PATH/pool` as an APT branch. See the **[REPOSITORY STRUCTURE](#repository-structure)** section for details.

*`zmq_change`*
:   The ZeroMQ IPC endpoint via which `p-vector` will send notifications about packages updates after each scan. Another program may listen on the endpoint to execute actions when packages are added, updated or deleted. This parameter is optional.

```{caption="ZeroMQ IPC Format"}
{
	'comp': branch/main,
	'pkg': package_name,
	'arch': aarch64,
	'method': overwrite | upgrade | delete | new,
	'from_ver': "0.0.0",
	'to_ver': "1.1.1"
}
```

After the global section come parameters for each branch. Each branch corresponds to a release as defined in the Debian Repository Format[^deb].

```{caption="Configuration file: Per-branch sections"}
 ... global parameters ...
---
branch: stable-local
ttl: 14
---
branch: testing-local
desc: "testing"
---
 ... more branch specific parameters if needed ...
```

*`branch_name`*
:   Name of the branch that parameters in the same section will be applied to. Binary `deb` packages for this branch must be stored in directory `$PATH/pool/$BRANCH_NAME/main`. This parameter must be specified exactly once in each per-branch section, and the same value should not appear in multiple per-branch sections.
:   This field is used as the _`Suite`_ field in the generated APT assets.

The following parameters can be either placed in the global section as default values or specified per-branch to override the defaults.

*`codename`*
:   A development codename for the software release, used as the _`Codename`_ field in _`InRelease`_.

*`desc`*
:   A human readable description for the branch. When description is not set for a branch, its description will be derived from the global default, with all occurrences of _`%BRANCH%`_ replaced by _`branch_name`_.
:   This value is used as the _`Description`_ field in the generated _`InRelease`_ files.

*`label`*
:   A short label for the branch. This will be the _`Label`_ field in the generated _`InRelease`_ files.

*`origin`*
:   A one-line phrase indicating the origin of the APT sources, used as the _`Origin`_ field in _`InRelease`_.

*`renew_in`*
:   The number of days before _`InRelease`_ expires when `p-vector` will regenerate APT assets regardless of whether any `deb` packages are added, updated or removed. This parameter is optional and defaults to 1 day if left unspecified. Setting this parameter to a value larger than _`ttl`_ will cause `p-vector` to always regenerate APT assets every time during a _`release`_ operation.

*`ttl`*
:   The number of days before the generated _`InRelease`_ is considered obsolete and outdated by APT.
:   This value is used to derive _`Valid-Until`_ field together with _`Date`_ in generated _`InRelease`_ files.

AOSC OS repository only has one component: _`main`_. Other fields in the Debian Repository Format are left empty for now, but support for them may be added in the future.

[^deb]: [Structure of the official Debian repository](https://wiki.debian.org/DebianRepository/Format). AOSC does not strictly adhere to this structure. Here this resource is presented for reference purposes. 
