from django.urls import reverse
from rest_framework import status

from constants import OBSERVATION_SET_KEY

from api.tests.base import BaseAPITestCase

class TestMetadataSetOperations(BaseAPITestCase):

    def setUp(self):
        self.establish_clients()

        self.set1 = {
            'elements': [
                {
                    'id':'foo',
                    'attributes': {
                        'keyA': {
                            'attribute_type': 'String',
                            'value': 'abc'
                        }
                    }
                },
                {
                    'id':'bar',
                    'attributes': {
                        'keyA': {
                            'attribute_type': 'String',
                            'value': 'abc'
                        }
                    }
                }
            ]
        }

        # none of the elements match set 1, so an intersection should be null set
        # and union should have length 3
        self.set2 = {
            'elements': [
                {
                    'id':'baz',
                    'attributes': {
                        'keyA': {
                            'attribute_type': 'String',
                            'value': 'abc'
                        }
                    }
                }
            ]
        }

        # intersection with set1 should basically produce an identical copy of set1
        # (all the nested attributes of 'foo' are the same)
        self.set3 = {
            'elements': [
                {
                    'id':'foo',
                    'attributes': {
                        'keyA': {
                            'attribute_type': 'String',
                            'value': 'abc'
                        }
                    }
                },
                {
                    'id':'baz',
                    'attributes': {
                        'keyA': {
                            'attribute_type': 'String',
                            'value': 'abc'
                        }
                    }
                }
            ]
        }

        # intersection with set1 should basically produce an identical copy of set1
        # EXCEPT that 'foo' has a different attribute (keyB) here. We should merge that
        # with the keyA on 'foo' in set1
        self.set4 = {
            'elements': [
                {
                    'id':'foo',
                    'attributes': {
                        'keyB': {
                            'attribute_type': 'String',
                            'value': 'def'
                        }
                    }
                }
            ]
        }

        # a final set that is distinct from the others so that we can test union/intersection
        # on >2 sets.
        self.set5 = {
            'elements': [
                {
                    'id':'xyz',
                    'attributes': {
                        'keyB': {
                            'attribute_type': 'String',
                            'value': 'abc'
                        }
                    }
                }
            ]
        }

        # if we intersect this with set1, we should get a ValidationError
        # since the keyA attribute has a different value. There is no way to 
        # guess at the proper resolution of that conflict, so we raise an exception.
        self.set6 = {
            'elements': [
                {
                    'id':'foo',
                    'attributes': {
                        'keyA': {
                            'attribute_type': 'String',
                            'value': 'def'
                        }
                    }
                }
            ]
        }

        self.empty_set = {
            'elements': []
        }

        self.intersect_url = reverse('metadata-intersect')
        self.union_url = reverse('metadata-union')
        self.difference_url = reverse('metadata-difference')


    def test_set_intersection(self):

        # perform an intersection where there are no common elements. null set result.
        payload = {
            'sets': [
                self.set1,
                self.set2
            ],
            'set_type': OBSERVATION_SET_KEY
        }
        response = self.authenticated_regular_client.post(self.intersect_url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        j = response.json()
        elements = j['elements']
        self.assertTrue(len(elements) == 0)

        # perform an intersection where there are no common elements. null set result.
        # Here, there are 3 sets to compare
        payload = {
            'sets': [
                self.set1,
                self.set2,
                self.set5
            ],
            'set_type': OBSERVATION_SET_KEY
        }
        response = self.authenticated_regular_client.post(self.intersect_url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        j = response.json()
        elements = j['elements']
        self.assertTrue(len(elements) == 0)

        # set1 and set3 share 'foo', both with keyA='abc'
        payload = {
            'sets': [
                self.set1,
                self.set3
            ],
            'set_type': OBSERVATION_SET_KEY
        }
        response = self.authenticated_regular_client.post(self.intersect_url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        j = response.json()
        elements = j['elements']
        self.assertTrue(len(elements) == 1)
        foo_element = j['elements'][0]
        self.assertEqual(foo_element['id'], 'foo')
        attr_dict = foo_element['attributes']
        self.assertTrue(len(attr_dict.keys()) == 1)
        self.assertTrue('keyA' in attr_dict.keys())
        expected_dict =  {'attribute_type': 'String',
                            'value': 'abc'}
        self.assertDictEqual(attr_dict['keyA'], expected_dict)

        # set1 and set4 share 'foo', but 'foo' in set1 has keyA='abc'
        # while 'foo' in set4 has keyB='def'. Test that the resulting
        # intersection merges those two distinct attributes
        payload = {
            'sets': [
                self.set1,
                self.set4
            ],
            'set_type': OBSERVATION_SET_KEY
        }
        response = self.authenticated_regular_client.post(self.intersect_url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        j = response.json()
        elements = j['elements']
        self.assertTrue(len(elements) == 1)
        foo_element = j['elements'][0]
        self.assertEqual(foo_element['id'], 'foo')
        attr_dict = foo_element['attributes']
        self.assertTrue(len(attr_dict.keys()) == 2)
        self.assertTrue('keyA' in attr_dict.keys())
        self.assertTrue('keyB' in attr_dict.keys())
        expected_dict1 =  {'attribute_type': 'String',
                            'value': 'abc'}
        self.assertDictEqual(attr_dict['keyA'], expected_dict1)
        expected_dict2 =  {'attribute_type': 'String',
                            'value': 'def'}
        self.assertDictEqual(attr_dict['keyB'], expected_dict2)

        # test the case with the attribute conflict
        payload = {
            'sets': [
                self.set1,
                self.set6
            ],
            'set_type': OBSERVATION_SET_KEY
        }
        response = self.authenticated_regular_client.post(
            self.intersect_url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # test a typo on the payload (setS instead of sets)
        payload = {
            'setS': [
                self.set1,
                self.set2
            ],
            'set_type': OBSERVATION_SET_KEY
        }
        response = self.authenticated_regular_client.post(self.intersect_url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


        # test a typo on the payload (obs instead of observation)
        payload = {
            'setS': [
                self.set1,
                self.set2
            ],
            'set_type': 'obs'
        }
        response = self.authenticated_regular_client.post(self.intersect_url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # test a missing set_type key
        payload = {
            'sets': [
                self.set1,
                self.set2
            ]
        }
        response = self.authenticated_regular_client.post(self.intersect_url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # test an empty set input
        payload = {
            'sets': [
                self.set1,
                self.empty_set
            ],
            'set_type': OBSERVATION_SET_KEY
        }
        response = self.authenticated_regular_client.post(self.intersect_url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        j = response.json()
        elements = j['elements']
        self.assertTrue(len(elements) == 0)

        # test an empty set input
        payload = {
            'sets': [
                self.empty_set
            ],
            'set_type': OBSERVATION_SET_KEY
        }
        response = self.authenticated_regular_client.post(self.intersect_url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # test an empty set input
        payload = {
            'sets': [],
            'set_type': OBSERVATION_SET_KEY
        }
        response = self.authenticated_regular_client.post(self.intersect_url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_set_union(self):

        # perform a union where there are no common elements.
        payload = {
            'sets': [
                self.set1,
                self.set2
            ],
            'set_type': OBSERVATION_SET_KEY
        }
        response = self.authenticated_regular_client.post(self.union_url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        j = response.json()
        elements = j['elements']
        self.assertTrue(len(elements) == 3)
        expected = ['foo','bar','baz']
        returned = [x['id'] for x in elements]
        self.assertCountEqual(expected, returned)

        # perform an intersection where there are no common elements. 
        # Here, there are 3 sets to compare
        payload = {
            'sets': [
                self.set1,
                self.set2,
                self.set5
            ],
            'set_type': OBSERVATION_SET_KEY
        }
        response = self.authenticated_regular_client.post(self.union_url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        j = response.json()
        elements = j['elements']
        self.assertTrue(len(elements) == 4)
        expected = ['foo','bar','baz', 'xyz']
        returned = [x['id'] for x in elements]
        self.assertCountEqual(expected, returned)


        # set1 and set4 share 'foo', but each 'foo' has different attributes.
        # Check that the attribute dict for 'foo' has been merged
        payload = {
            'sets': [
                self.set1,
                self.set4
            ],
            'set_type': OBSERVATION_SET_KEY
        }
        response = self.authenticated_regular_client.post(self.union_url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        j = response.json()
        elements = j['elements']
        self.assertTrue(len(elements) == 2)
        el_dict = {x['id']:x for x in elements}
        foo_element = el_dict['foo']
        attr_dict = foo_element['attributes']
        self.assertTrue(len(attr_dict.keys()) == 2)
        self.assertTrue('keyA' in attr_dict.keys())
        self.assertTrue('keyB' in attr_dict.keys())
        expected_dict1 =  {'attribute_type': 'String',
                            'value': 'abc'}
        self.assertDictEqual(attr_dict['keyA'], expected_dict1)
        expected_dict2 =  {'attribute_type': 'String',
                            'value': 'def'}
        self.assertDictEqual(attr_dict['keyB'], expected_dict2)


        # test the case with the attribute conflict
        payload = {
            'sets': [
                self.set1,
                self.set6
            ],
            'set_type': OBSERVATION_SET_KEY
        }
        response = self.authenticated_regular_client.post(self.union_url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # test a typo on the payload (setS instead of sets)
        payload = {
            'setS': [
                self.set1,
                self.set2
            ],
            'set_type': OBSERVATION_SET_KEY
        }
        response = self.authenticated_regular_client.post(self.union_url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


        # test a typo on the payload (obs instead of observation)
        payload = {
            'setS': [
                self.set1,
                self.set2
            ],
            'set_type': 'obs'
        }
        response = self.authenticated_regular_client.post(self.union_url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # test a missing set_type key
        payload = {
            'sets': [
                self.set1,
                self.set2
            ]
        }
        response = self.authenticated_regular_client.post(self.union_url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # test an empty set input
        payload = {
            'sets': [
                self.set1,
                self.empty_set
            ],
            'set_type': OBSERVATION_SET_KEY
        }
        response = self.authenticated_regular_client.post(self.union_url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        j = response.json()
        elements = j['elements']
        self.assertTrue(len(elements) == 2)
        expected = ['foo','bar']
        returned = [x['id'] for x in elements]
        self.assertCountEqual(expected, returned)

        # test an empty set input
        payload = {
            'sets': [
                self.empty_set
            ],
            'set_type': OBSERVATION_SET_KEY
        }
        response = self.authenticated_regular_client.post(self.union_url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_set_difference(self):

        # perform a difference where there are no common elements.
        payload = {
            'sets': [
                self.set1,
                self.set2
            ],
            'set_type': OBSERVATION_SET_KEY
        }
        response = self.authenticated_regular_client.post(self.difference_url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        j = response.json()
        elements = j['elements']
        self.assertTrue(len(elements) == 2)
        expected = ['foo','bar']
        returned = [x['id'] for x in elements]
        self.assertCountEqual(expected, returned)

        # set 1 has foo, bar and set3 has foo and baz. shoudl return bar
        payload = {
            'sets': [
                self.set1,
                self.set3
            ],
            'set_type': OBSERVATION_SET_KEY
        }
        response = self.authenticated_regular_client.post(self.difference_url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        j = response.json()
        elements = j['elements']
        self.assertTrue(len(elements) == 1)
        expected = ['bar']
        returned = [x['id'] for x in elements]
        self.assertCountEqual(expected, returned)

        # set 1 has foo, bar and set3 has foo and baz. shoudl return baz
        # since order matters here!
        payload = {
            'sets': [
                self.set3,
                self.set1
            ],
            'set_type': OBSERVATION_SET_KEY
        }
        response = self.authenticated_regular_client.post(self.difference_url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        j = response.json()
        elements = j['elements']
        self.assertTrue(len(elements) == 1)
        expected = ['baz']
        returned = [x['id'] for x in elements]
        self.assertCountEqual(expected, returned)

        # set 4 and 6 both have only 'foo'. Technically the keyA attribute has
        # a different value, but for the set difference we ignore that
        payload = {
            'sets': [
                self.set4,
                self.set6
            ],
            'set_type': OBSERVATION_SET_KEY
        }
        response = self.authenticated_regular_client.post(self.difference_url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        j = response.json()
        elements = j['elements']
        self.assertTrue(len(elements) == 0)

        # the set diff endpoint will only take pairs. don't want to handle 
        # more than two sets since it's not clear to most users how that would work
        payload = {
            'sets': [
                self.set1,
                self.set4,
                self.set6
            ],
            'set_type': OBSERVATION_SET_KEY
        }
        response = self.authenticated_regular_client.post(self.difference_url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        payload = {
            'sets': [
                self.set1
            ],
            'set_type': OBSERVATION_SET_KEY
        }
        response = self.authenticated_regular_client.post(self.difference_url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        payload = {
            'sets': [],
            'set_type': OBSERVATION_SET_KEY
        }
        response = self.authenticated_regular_client.post(self.difference_url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # test the case 
        payload = {
        "sets": [
            {
                "elements": [
                    {
                    "id": "D20_175135"
                    },
                    {
                    "id": "D20_1989"
                    }
                ]
            },
            {
                "elements": [
                    {
                        "id": "D20_1989",
                        "attributes": {
                            "cell_type": "CD4",
                            "sequencing_run": "MIT_2"
                        }
                    }
                ]
            }
        ],
        "set_type": OBSERVATION_SET_KEY
        }
        response = self.authenticated_regular_client.post(self.difference_url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        payload['ignore_attributes'] = True
        response = self.authenticated_regular_client.post(self.difference_url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        j = response.json()
        elements = j['elements']
        self.assertTrue(len(elements) == 1)
        expected = ['D20_175135']
        returned = [x['id'] for x in elements]
        self.assertCountEqual(expected, returned)
