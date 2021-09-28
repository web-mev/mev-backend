After installing solr, create a core. This is run as the vagrant user:

```
/opt/solr/bin/solr create_core -c tcga-rnaseq -d /vagrant/mev/api/public_data/gdc/solr/tcga_rnaseq
```

Next, created an example annotation file using the test script. Index that:

```
/opt/solr/bin/post -c tcga-rnaseq /vagrant/mev/public_data/tcga/ann.csv
```

Then, to query, we can use the requests library.

For example, below we query on the cancer types in the dataset using a faceted query:

```python
>>> import requests
>>> params = {'facet.field':'project_id', 'facet': 'on', 'q':'*:*', 'rows':0}
>>> url = 'http://localhost:8983/solr/tcga-rnaseq/select'
>>> r = requests.get(url, params=params)
>>> print(json.dumps(r.json(), indent=3))
{
   "responseHeader": {
      "status": 0,
      "QTime": 2,
      "params": {
         "q": "*:*",
         "facet.field": "project_id",
         "rows": "0",
         "facet": "on"
      }
   },
   "response": {
      "numFound": 166,
      "start": 0,
      "numFoundExact": true,
      "docs": []
   },
   "facet_counts": {
      "facet_queries": {},
      "facet_fields": {
         "project_id": [
            "TCGA-MESO",
            86,
            "TCGA-UVM",
            80
         ]
      },
      "facet_ranges": {},
      "facet_intervals": {},
      "facet_heatmaps": {}
   }
}
```

To list the available cores, run:

```python
>>> import requests
>>> import json
>>> url = 'http://localhost:8983/solr/admin/cores'
>>> params = {'actions': 'list'}
>>> r = requests.get(url, params=params)
>>> r
<Response [200]>
>>> print(json.dumps(r.json(), indent=3))
{
   "responseHeader": {
      "status": 0,
      "QTime": 1
   },
   "initFailures": {},
   "status": {
      "tcga-rnaseq": {
         "name": "tcga-rnaseq",
         "instanceDir": "/var/solr/data/tcga-rnaseq",
         "dataDir": "/var/solr/data/tcga-rnaseq/data/",
         "config": "solrconfig.xml",
         "schema": "schema.xml",
         "startTime": "2021-07-20T19:50:23.861Z",
         "uptime": 2213750,
         "index": {
            "numDocs": 166,
            "maxDoc": 166,
            "deletedDocs": 0,
            "indexHeapUsageBytes": 13436,
            "version": 6,
            "segmentCount": 1,
            "current": true,
            "hasDeletions": false,
            "directory": "org.apache.lucene.store.NRTCachingDirectory:NRTCachingDirectory(MMapDirectory@/var/solr/data/tcga-rnaseq/data/index lockFactory=org.apache.lucene.store.NativeFSLockFactory@79c518fe; maxCacheMB=48.0 maxMergeSizeMB=4.0)",
            "segmentsFile": "segments_2",
            "segmentsFileSizeInBytes": 220,
            "userData": {
               "commitTimeMSec": "1626811153212",
               "commitCommandVer": "1705835131789377536"
            },
            "lastModified": "2021-07-20T19:59:13.212Z",
            "sizeInBytes": 88589,
            "size": "86.51 KB"
         }
      }
   }
}
```