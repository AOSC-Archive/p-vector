
install(FILES
        deb822.py
        internal_db.py
        internal_dpkg_version.py
        internal_pkgscan.py
        module_ipc.py
        module_release.py
        module_scan.py
        module_sync.py
        module_check_elf.py
        vercomp.sql
        abbsdb.sql
        pkgissues.sql
        DESTINATION ${LIBEXEC_PATH})
