alter table pv_package_sodep add constraint fkey_package foreign key (package, version, repo) references pv_packages (package, version, repo) on delete cascade;
alter table pv_package_sodep alter constraint fkey_package initially deferred;

alter table pv_package_files add constraint fkey_package foreign key (package, version, repo) references pv_packages (package, version, repo) on delete cascade;
alter table pv_package_files alter constraint fkey_package initially deferred;

alter table pv_package_dependencies add constraint fkey_package foreign key (package, version, repo) references pv_packages (package, version, repo) on delete cascade;
alter table pv_package_dependencies alter constraint fkey_package initially deferred;

alter table pv_package_duplicate add constraint fkey_package foreign key (package, version, repo) references pv_packages (package, version, repo) on delete cascade;
alter table pv_package_duplicate alter constraint fkey_package initially deferred;

alter table pv_packages add constraint fkey_repo foreign key (repo) references pv_repos (name) on delete cascade;
alter table pv_packages alter constraint fkey_repo initially deferred;
