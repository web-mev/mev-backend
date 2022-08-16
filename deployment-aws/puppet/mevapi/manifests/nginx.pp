class mevapi::nginx () {
  class { 'nginx':
    confd_purge => true,  # remove default config
  }
  nginx::resource::upstream { 'mev_app':
    members => {
      'gunicorn' => {
        server       => 'unix:/tmp/gunicorn.sock',
        # always retry an upstream even if it failed to return a good HTTP response
        fail_timeout => '0s',
      }
    }
  }
  # This map helps in situations where the request doesn't reach the
  # gunicorn application server. An example is when the payload
  # exceeds the client_max_body_size. In that case, nginx immediately
  # responds with a 413, and the frontend is unable to
  # see the response since it was lacking the 'Access-Control-Allow-Origin'
  # header. This map skips editing in the case where this header exists and
  # adds it in the case where it does not.
  nginx::resource::map { 'cors_origin':
    string   => '$upstream_http_access_control_allow_origin',
    default  => "''",
    mappings => {
      "''" => '$http_origin'
    },
  }
  nginx::resource::server { $mevapi::backend_domain:
    listen_port          => 80,
    client_max_body_size => '256m',
    use_default_location => false,
    index_files          => [],
    locations            => {
      'root'   => {
        location         => '/',
        add_header       => {
          'Access-Control-Allow-Origin' => { '$cors_origin' => 'always' },
        },
        proxy            => 'http://mev_app',
        proxy_redirect   => 'off',
        proxy_set_header => [
          'Host              $host',
          'X-Forwarded-For   $proxy_add_x_forwarded_for',
          'X-Forwarded-Proto $scheme',
          'X-Forwarded-Host  $host',
          'X-Forwarded-Port  $server_port',
        ],
      },
      'static' => {
        location       => '/static/',
        location_alias => "${mevapi::django::static_root}/",
        index_files    => [],
      },
    },
  }
  nginx::resource::server { 'default':
    server_name         => ['_'],
    listen_port         => 80,
    listen_options      => "default_server",
    index_files         => [],
    access_log          => 'absent',
    error_log           => 'absent',
    location_custom_cfg => {
      'return' => 444,
    }
  }
}
