import requests
import json
import sys


DICTIONARY_ENDPOINT = 'https://api.gdc.cancer.gov/v0/submission/_dictionary/{attribute}?format=json'

IGNORED_PROPERTIES = [
    'cases',
    'state',
    'type',
    'updated_datetime',
    'created_datetime',
    'id',
    'submitter_id',
    'releasable',
    'released',
    'intended_release_date',
    'batch_id',
    'programs'
]
ATTRIBUTES = [
    'demographic',
    'diagnosis',
    'exposure',
    'project'
]

def get_data_dict():
    d = {}
    for attr in ATTRIBUTES:
        property_list = []
        url = DICTIONARY_ENDPOINT.format(attribute = attr)
        response = requests.get(url)
        j = response.json()
        properties = j['properties']

        for k in properties.keys():
            if k in IGNORED_PROPERTIES:
                continue
            try:
                description = properties[k]['description']
            except KeyError as ex:
                description = None
            property_list.append({
                'field': k,
                'description': description
            })
        d[attr] = property_list
    return d