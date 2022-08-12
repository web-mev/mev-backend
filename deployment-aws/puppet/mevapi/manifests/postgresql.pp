class mevapi::postgresql () {
  if $mevapi::platform == 'aws' {
    class { 'postgresql::server':
      service_manage           => false,
      manage_pg_hba_conf       => false,
      manage_pg_ident_conf     => false,
      manage_recovery_conf     => false,
      default_connect_settings => {
        'PGHOST'     => $mevapi::database_host,
        'PGPORT'     => '5432',
        'PGUSER'     => $mevapi::database_superuser,
        'PGPASSWORD' => $mevapi::database_superuser_password,
      }
    }
  }
  else {
    class { 'postgresql::server': }
  }

  # workaround for https://tickets.puppetlabs.com/browse/MODULES-5068
  postgresql::server::role { $mevapi::database_user:
    password_hash   => $mevapi::database_user_password,
    update_password => false,
  }
  ->
  postgresql::server::db { 'webmev':
    user     => $mevapi::database_user,
    password => $mevapi::database_user_password,
    owner    => $mevapi::database_user,
  }
}
