class mevapi::solr () {
  $solr_home = "${mevapi::data_root}/solr"

  class { 'solr':
    version     => '8.11.1',  # make sure luceneMatchVersion in all solrconfig.xml files matches this version
    solr_home   => $solr_home,
    schema_name => 'schema.xml',  # classic schema
  }
  file { "${solr_home}/solr.xml":
    ensure => file,
    source => "${mevapi::project_root}/solr/solr.xml",
    owner  => $::solr::solr_user,
    group  => $::solr::solr_user,
  }

  # Ensures that everything under the solr dir is owned by the solr user.
  # Depending on the ordering of solr and cloudwatch agent, there can be 
  # situations where UIDs on different systems can result in files which
  # are not owned by the correct user.
  # TODO: once data volume recovery scripts are prepared, this can likely
  #       be removed.
  file { "${solr_home}":
    ensure  => directory,
    owner   => $::solr::solr_user,
    group   => $::solr::solr_user,
    recurse => true
  }

  solr::core { 'tcga-rnaseq':
    schema_src_file     => "${mevapi::project_root}/solr/tcga-rnaseq/schema.xml",
    solrconfig_src_file => "${mevapi::project_root}/solr/tcga-rnaseq/solrconfig.xml",
  }
  solr::core { 'target-rnaseq':
    schema_src_file     => "${mevapi::project_root}/solr/target-rnaseq/schema.xml",
    solrconfig_src_file => "${mevapi::project_root}/solr/target-rnaseq/solrconfig.xml",
  }
  solr::core { 'gtex-rnaseq':
    schema_src_file     => "${mevapi::project_root}/solr/gtex-rnaseq/schema.xml",
    solrconfig_src_file => "${mevapi::project_root}/solr/gtex-rnaseq/solrconfig.xml",
  }
  solr::core { 'tcga-micrornaseq':
    schema_src_file     => "${mevapi::project_root}/solr/tcga-micrornaseq/schema.xml",
    solrconfig_src_file => "${mevapi::project_root}/solr/tcga-micrornaseq/solrconfig.xml",
  }

}
