from .element import BaseElement

class Observation(BaseElement):
    '''
    An `Observation` is the generalization of a "sample" in the typical context
    of biological studies.  One may think of samples and observations as 
    interchangeable concepts.  We call it an observation so that we are not 
    limited by this convention, however.

    `Observation` instances act as metadata and can be used to filter and subset
    the data to which it is associated/attached.

    An `Observation` is structured as:
    ```
    {
        "id": <string identifier>,
        "attributes": {
            "keyA": <Attribute>,
            "keyB": <Attribute>
        }
    }
    ```
 
    '''

    def __init__(self, id, attribute_dict={}):
        super().__init__(id, attribute_dict)


    def __repr__(self):
        return 'Observation ({id})'.format(id=self.id)