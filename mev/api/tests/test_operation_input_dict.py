import unittest
import uuid
import random

from resource_types import RESOURCE_MAPPING
from api.serializers.operation_input_dict import OperationInputDictSerializer
from api.serializers.operation_input import OperationInputSerializer
from api.serializers.operation_output import OperationOutputSerializer
from api.data_structures import OperationInputDict

class OperationInputDictTester(unittest.TestCase):
    def setUp(self):

        all_resource_types = list(RESOURCE_MAPPING.keys())
        random.shuffle(all_resource_types)

        # an OperationInput
        self.op_input1_dict = {
            'description': 'The count matrix of expressions',
            'name': 'Count matrix:',
            'required': True,
            'converter': '...',
            'spec': {
                'attribute_type': 'DataResource',
                'resource_type': all_resource_types[0],
                'many': False
            }
        }
        # another OperationInput
        self.op_input2_dict={
            'description': 'The filtering threshold for the p-value',
            'name': 'P-value threshold:',
            'required': False,
            'converter': '...',
            'spec': {
                'attribute_type': 'BoundedFloat',
                'min': 0,
                'max': 1.0,
                'default': 0.05
            }
        }

        self.op_input1 = OperationInputSerializer(data=self.op_input1_dict).get_instance()
        self.op_input2 = OperationInputSerializer(data=self.op_input2_dict).get_instance()

        self.operation_input_dict = {
            'count_matrix': self.op_input1_dict,
            'p_val': self.op_input2_dict
        }

    def test_serialization(self):
        oid = OperationInputDict({
            'count_matrix': self.op_input1,
            'p_val': self.op_input2
        })
        oid_serializer = OperationInputDictSerializer(oid)
        expected_data = self.operation_input_dict.copy()
        self.assertDictEqual(oid_serializer.data, expected_data)

        o = OperationInputDictSerializer(data={
            'count_matrix': self.op_input1_dict,
            'p_val': self.op_input2_dict
        })
        expected_data = self.operation_input_dict.copy()
        i = o.get_instance()
        self.assertDictEqual(i.to_dict(), expected_data)

    def test_deserialization(self):
        o = OperationInputDictSerializer(data=self.operation_input_dict)
        i = o.get_instance()
        self.assertEqual(i['count_matrix'], self.op_input1)
        self.assertEqual(i['p_val'], self.op_input2)

        d = i.to_dict()
        self.assertDictEqual(d, self.operation_input_dict)