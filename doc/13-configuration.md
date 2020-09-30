### Configuration

A single `p-vector` instance manages exactly one APT pool and one dist directory. An instance of `p-vector` consists of a configuration YAML and a PostgreSQL database.

##### PostgreSQL

You will need a PostgreSQL database for `p-vector` to retain its state information about the APT repository and packages. Assuming `p-vector` is installed to `/usr/bin/p-vector`, run the following in your shell to bootstrap a database for use with `p-vector`:

```{caption="Bootstrapping database"}
psql $DB_NAME < /usr/libexec/p-vector/abbsdb.sql
psql $DB_NAME < /usr/libexec/p-vector/vercomp.sql
```

##### YAML

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
desc: "Cooked Jelly for %BRANCH%"
---
 ... branch specific parameters ...
---
 ... branch specific parameters ...
```

Here we explain the global parameters that affects `p-vector` itself:

*`db_pgconn`*
:   Accepts a set of connection parameters in the form of a PostgreSQL connection string[^connstring]. This specifies the PostgreSQL database where `p-vector` stores package metadata. The database must exist and the invoking user must have read-write permission to the database. For local usage, single _`dbname=blah`_ should be enough.

[^connstring]: See [PostgreSQL Documentation](https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING) on how to specify a database connection.

*`path`*
:   Accepts a path where `p-vector` will search for `deb` packages and place generated APT assets. See **[REPOSITORY STRUCTURE](#repository-structure)** section for more information.

*`zmq_change`*
:   The ZeroMQ IPC endpoint via which `p-vector` will send notification about packages updated after each scan. The message itself consists of key-value pairs in JSON representation as the following. Another program may listen on the endpoint to execute actions when packages are added, updated or deleted. This parameter is optional.

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

*`populate`*
:   Accepts a boolean value. This parameter controls whether `p-vector` should implicitly treat all directories under `$PATH/pool` as an APT branch. See **[REPOSITORY STRUCTURE](#repository-structure)** section for more information.


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

After the global section come parameters for each branch. Each branch corresponds to a release as defined in the Debian Repository Format[^deb].

*`branch_name`*
:   Name of the branch that parameters in the same section will be applied to. Binary `deb` packages for this branch must be stored in directory `$PATH/pool/$BRANCH_NAME/main`. This parameter must be specified exactly once in each per-branch section, and the same value should not appear in multiple per-branch sections.
:   This field is used as the _`Suite`_ field in the generated APT assets.

The following parameters can be either placed in the global section as default values or specified per-branch to override the defaults.

*`label`*
:   A short label for the branch. This will be the _`Label`_ field in the generated _`InRelease`_ files.

*`desc`*
:   A human readable description for the branch. When description is not set for a branch, its description will be derived from the global default, with all occurrences of _`%BRANCH%`_ replaced by _`branch_name`_.
:   This value is used as the _`Description`_ field in the generated _`InRelease`_ files.

*`ttl`*
:   The number of days before the generated _`InRelease`_ is considered obsolete and outdated.
:   This value is used to derive _`Valid-Until`_ field together with _`Date`_ in generated _`InRelease`_ files.

*`codename`*
:   A one-word development codename for the software release, used as the _`Codename`_ field in _`InRelease`_.

*`origin`*
:   A one-line phrase indicating the origin of the APT sources, used as the _`Origin`_ field in _`InRelease`_.

AOSC OS repository only has one component: _`main`_. Other fields in the Debian Repository Format are not supported for now, but may be added in the future.

[^deb]: [Structure of the official Debian repository](https://wiki.debian.org/DebianRepository/Format). AOSC does not strictly adhere to this structure, but this is retained for reference nonetheless. 
