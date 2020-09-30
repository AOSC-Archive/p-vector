### Repository Structure

`p-vector` sets forth the following expectations for directory structure specified by _`path`_ in each YAML file:

*`pool/$BRANCH`*
:   A single branch. In typical AOSC deployments before the topic-based iteration system, there were multiple branches - `stable`, `testing`, etc. To include a branch that exists on disk in the repository, the YAML file _must either_ specify the _`populate`_ parameter in the global section, _or_ has a per-branch section with _`branch_name`_ set to the name of the directory, as is specified in the **[Configuration - YAML](#yaml)** section.

*`pool/$BRANCH/$COMPONENT`*
:   Contains actual `deb` packages for this component from where `p-vector` will monitor for changes. `p-vector` does not impose requirements on structure in this directory, but users are advised to follow the Debian convention to organize packages into subdirectories by the first letter of their names. This is also the default structure in your output directory if you are building packages with [Autobuild3](https://github.com/AOSC-Dev/autobuild3):

        pool/$BRANCH/$COMPONENT/a/aaa_1.0.0-0_amd64.deb
        pool/$BRANCH/$COMPONENT/libc/libc_1.0.0-0_amd64.deb

*`dist/$BRANCH`*
:   For every branch scanned, `p-vector` populates a directory with the same name with APT readable metadata for this branch.

*`dist/$BRANCH/InRelease`*
:   A PGP "clear signed" text with the general information about branches and checksums of other APT metadata files.

*`dist/$BRANCH/$COMPONENT/Contents-$ARCHITECTURE.gz`*
:   Gzipped list of mappings from a path to the section-package that provides this path.

*`dist/$BRANCH/$COMPONENT/binary-$ARCHITECTURE/Packages.xz`*
:   Xzipped list of package metadata: names, versions, file names, checksums, dependencies, etc.

The whole _`path`_ can now be published to an external hosting service or used locally as an APT repository.
