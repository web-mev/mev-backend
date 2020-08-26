import unittest
import uuid
import random

from resource_types import RESOURCE_MAPPING
from api.serializers.operation_output_dict import OperationOutputDictSerializer
from api.serializers.operation_output import OperationOutputSerializer

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
        o = OperationOutputDictSerializer({
            'abc': self.op_output1,
            'xyz': self.op_output2
        })
        expected_data = self.operation_output_dict.copy()
        self.assertDictEqual(o.data, expected_data)

    def test_deserialization(self):
        o = OperationOutputDictSerializer(data=self.operation_output_dict)
        i = o.get_instance()
        self.assertEqual(i['abc'], self.op_output1)
        self.assertEqual(i['xyz'], self.op_output2)