class mevapi::python () {
  class { 'python':
    version => '3.8',
  }

  python::requirements { "${django_root}/requirements.txt":
    pip_provider           => 'pip3',
    forceupdate            => true,
    fix_requirements_owner => false,
  }
}
