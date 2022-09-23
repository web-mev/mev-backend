from .element import BaseElement

class Feature(BaseElement):
    '''
    A `Feature` can also be referred to as a covariate or variable.  
    These are measurements one can make about an `Observation`.  For example,
    in the genomics context, a sample can have 30,000+ genes which we call
    "features" here.  In the statistical learning context, these are feature vectors.

    `Feature` instances act as metadata and can be used to filter and subset
    the data to which it is associated/attached.  For example, we can imagine
    filtering by genes/features which have a particular value, such as those genes
    where the attribute "oncogene" is set to "true" 

    A `Feature` is structured as:
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
    def __repr__(self):
        return 'Feature ({id})'.format(id=self._id)