node /api/ {
  class { 'mevapi':
    admin_email_csv             => $facts['admin_email_csv'],
    backend_domain              => $facts['backend_domain'],
    database_host               => $facts['database_host'],
    database_superuser          => $facts['database_superuser'],
    database_superuser_password => $facts['database_superuser_password'],
    database_user_password      => $facts['database_user_password'],
    django_superuser_password   => $facts['django_superuser_password'],
  }
}
