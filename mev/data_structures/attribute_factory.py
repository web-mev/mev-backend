from copy import deepcopy

from data_structures.factory import BaseAttributeFactory
from data_structures.simple_attribute_factory import \
    simple_attribute_type_mapping

# these are "compound" data structures since they may contain
# other attributes. For instance, Observation may contain a dict
# containing simple types like PositiveIntegerAttribute, etc.
from data_structures.observation import Observation
from data_structures.feature import Feature
from data_structures.observation_set import ObservationSet
from data_structures.feature_set import FeatureSet

attribute_types = [
    Observation,
    Feature,
    ObservationSet,
    FeatureSet
]
# Note the deepcopy. Otherwise we end up modifying the 
# simple attribute types which determine which types can be 
# created by the SimpleAttributeFactory.
attribute_type_mapping = deepcopy(simple_attribute_type_mapping)
attribute_type_mapping.update(
    {x.typename: x for x in attribute_types}
)

def AttributeFactory(val, allow_null=False):
    return BaseAttributeFactory(
        val, attribute_type_mapping, allow_null=allow_null)