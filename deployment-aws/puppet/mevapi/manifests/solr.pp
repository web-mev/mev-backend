class mevapi::solr () {
  $solr_home = "${mevapi::data_root}/solr"

  class { 'solr':
    version     => '8.11.1',  # make sure luceneMatchVersion in all solrconfig.xml files matches this version
    solr_home   => $solr_home,
    schema_name => 'schema.xml',  # classic schema
  }
  file { "${solr_home}/solr.xml":
    ensure => file,
    source => "${project_root}/solr/solr.xml",
    owner  => $::solr::solr_user,
    group  => $::solr::solr_user,
  }
  solr::core { 'tcga-rnaseq':
    schema_src_file     => "${project_root}/solr/tcga-rnaseq/schema.xml",
    solrconfig_src_file => "${project_root}/solr/tcga-rnaseq/solrconfig.xml",
  }
  solr::core { 'target-rnaseq':
    schema_src_file     => "${project_root}/solr/target-rnaseq/schema.xml",
    solrconfig_src_file => "${project_root}/solr/target-rnaseq/solrconfig.xml",
  }
  solr::core { 'gtex-rnaseq':
    schema_src_file     => "${project_root}/solr/gtex-rnaseq/schema.xml",
    solrconfig_src_file => "${project_root}/solr/gtex-rnaseq/solrconfig.xml",
  }

}
