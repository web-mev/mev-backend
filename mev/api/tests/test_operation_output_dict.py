import unittest
import uuid
import random

from resource_types import RESOURCE_MAPPING
from api.serializers.operation_output_dict import OperationOutputDictSerializer
from api.serializers.operation_output import OperationOutputSerializer
from api.data_structures import OperationOutputDict

class OperationOutputDictTester(unittest.TestCase):
    def setUp(self):

        all_resource_types = list(RESOURCE_MAPPING.keys())
        random.shuffle(all_resource_types)

        self.op_output1_dict = {
            'spec': {
                'attribute_type': 'DataResource',
                'resource_type': all_resource_types[0],
                'many': False
            }
        }
        self.op_output2_dict = {
            'spec': {
                'attribute_type': 'BoundedInteger',
                'max': 10,
                'min':0
            }
        }

        self.op_output1 = OperationOutputSerializer(data=self.op_output1_dict).get_instance()
        self.op_output2 = OperationOutputSerializer(data=self.op_output2_dict).get_instance()

        self.operation_output_dict = {
            'abc': self.op_output1_dict,
            'xyz': self.op_output2_dict
        }

    def test_serialization(self):
        o = OperationOutputDict({
            'abc': self.op_output1,
            'xyz': self.op_output2
        })
        ods = OperationOutputDictSerializer(o)
        expected_data = self.operation_output_dict.copy()
        self.assertDictEqual(ods.data, expected_data)

    def test_deserialization(self):
        o = OperationOutputDictSerializer(data=self.operation_output_dict)
        i = o.get_instance()
        self.assertEqual(i['abc'], self.op_output1)
        self.assertEqual(i['xyz'], self.op_output2)

    def test_equality(self):
        '''
        Tests that the '==' overload works as expected.
        '''
        od1 = {
            'spec': {
                'attribute_type': 'BoundedInteger',
                'max': 10,
                'min':0
            }
        }
        od2 = {
            'spec': {
                'attribute_type': 'BoundedInteger',
                'max': 10,
                'min':0
            }
        }
        od3 = {
            'spec': {
                'attribute_type': 'Integer',
            }
        }

        # check strict equality
        x1 = {
            'keyA': od1,
            'keyB': od2
        }
        x2 = {
            'keyA': od1,
            'keyB': od2
        }
        i1 = OperationOutputDictSerializer(data=x1).get_instance()
        i2 = OperationOutputDictSerializer(data=x2).get_instance()
        self.assertEqual(i1,i2)

        # give an extra key to the second dict
        x1 = {
            'keyA': od1,
            'keyB': od2
        }
        x2 = {
            'keyA': od1,
            'keyB': od2,
            'keyC': od3
        }
        i1 = OperationOutputDictSerializer(data=x1).get_instance()
        i2 = OperationOutputDictSerializer(data=x2).get_instance()
        self.assertNotEqual(i1,i2)

        # different keys in each dict
        x1 = {
            'keyA': od1,
            'keyB': od2
        }
        x2 = {
            'keyA': od1,
            'keyC': od2
        }
        i1 = OperationOutputDictSerializer(data=x1).get_instance()
        i2 = OperationOutputDictSerializer(data=x2).get_instance()
        self.assertNotEqual(i1,i2)

        # same keys, but different vals
        x1 = {
            'keyA': od1,
            'keyB': od2
        }
        x2 = {
            'keyA': od1,
            'keyB': od3
        }
        i1 = OperationOutputDictSerializer(data=x1).get_instance()
        i2 = OperationOutputDictSerializer(data=x2).get_instance()
        self.assertNotEqual(i1,i2)