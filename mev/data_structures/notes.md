

Pretend we are trying to validate and `Operation` instance. The operation spec file looks like (in part):
```
{
    "name": "...", 
    "description": "...", 
    "inputs": {
        "raw_counts": {
            "description": "The input raw count matrix. Must be an integer-based table.", 
            "name": "Count matrix:", 
            "required": true, 
            "spec": {
                "attribute_type": "VariableDataResource", 
                "resource_types": ["I_MTX", "RNASEQ_COUNT_MTX"], 
                "many": false
            }
        }, 
        "base_sample": {
            "description": "The set of samples that are in the \"base\" or \"control\" condition.", 
            "name": "Control/base group samples:", 
            "required": true, 
            "spec": {
                "attribute_type": "ObservationSet"
            }
        },
        "other_samples": {
            "description": "The set of samples that are in the \"treated\" or \"experimental\" condition.", 
            "name": "Treated/experimental samples:", 
            "required": true, 
            "spec": {
                "attribute_type": "ObservationSet"
            }
        }
    }, 
    "outputs": {...}, 
    ...
}
```

Consider validating the `inputs` content. We first look at `raw_counts`:

```
{
    "description": "The input raw count matrix. Must be an integer-based table.", 
    "name": "Count matrix:", 
    "required": true, 
    "spec": {
        "attribute_type": "VariableDataResource", 
        "resource_types": ["I_MTX", "RNASEQ_COUNT_MTX"], 
        "many": false
}
```
In particular, we are interested in the `spec`. We pass that to the constructor of `data_structures.attribute.Attribute`. Since there is no `default` key, that gets sets to `None`. Thus, the constructor of `Attribute` receives:
```
{
        "attribute_type": "VariableDataResource", 
        "resource_types": ["I_MTX", "RNASEQ_COUNT_MTX"], 
        "value": None
        "many": False
}
```
along with `allow_null=True`. In that constructor, we strip off `attribute_type` and `value`, but add on `allow_null`. Hence, the constructor for the `VariableDataResourceAttribute` is called with:
```
VariableDataResourceAttribute.__init__(
    None,
    {
        "resource_types": ["I_MTX", "RNASEQ_COUNT_MTX"], 
        "many": False",
        "allow_null": True
    }    
)
```
Looks good.

Next, consider the `Observation` input `base_sample`:
```
{
    "description": "...", 
    "name": "...", 
    "required": true, 
    "spec": {
        "attribute_type": "Observation"
    }
}
```
The `spec` field is passed to the `Attribute` constructor, along with `allow_null=True`. As before, since there is no `default` key, we set `value` to None. Thus, the constructor receives a dict like:
```
{
    "attribute_type": "Observation",
    "value": None
}
```
The `attribute_type` and `value` keys are popped, leaving only `allow_null` in the kwargs passed to the constructor of `Observation`. The constructor for `Observation` works up to the constructor of `Element`. There is nothing to do.

Let's consider the situation where there is a default value (note that this doesn't really make sense, but run with it here...). 

`Observation` instances can contain a dictionary of key-value pairs which reference (typically)
simple metadata about a sample. For instance, below we use age (which is required to be a positive int.)
```
{
    "description": "...", 
    "name": "...", 
    "required": true, 
    "spec": {
        "attribute_type": "Observation",
        "default": {
            "id": "mySample",
            "attributes": {
                "age: {
                    "attribute_type": "PositiveInteger",
                    "value": 5
                }
            }
        }
    }
}
```
So, in this case we need to verify that the default value is acceptable. The `Attribute` constructor gets:
```
{
    "attribute_type": "Observation",
    "value": {
        "id": "mySample",
        "attributes": {
            "age: {
                "attribute_type": "PositiveInteger",
                "value": 5
            }
        }
    }
}
```
Thus, we attempt to instantiate an instance of `Observation` where we pass the following to the constructor of `Observation`:
```
Observation.__init__(
    {
        "id": "mySample",
        "attributes": {
            "age: {
                "attribute_type": "PositiveInteger",
                "value": 5
            }
        }
    },
    allow_null=False
)
```
Within the logic of the `Element` class, we then iterate through the `attributes` dict and attempt instantiation of each attribute. For instance, `age` is:
```
{
    "attribute_type": "PositiveInteger",
    "value": 5   
}
```
which is a valid object for `PositiveIntegerAttribute` type.

Thus, in the `Observation` class, we set an `id` member to the string `"mySample"` and the `attributes` member to a dict where the keys are strings and the "values" are instances of `BaseAttributeType`. For example, if we have
an instance of an `Observation` (call this `myObs`), then `myObs.id` returns `"mySample"` and `myObs.attributes` returns:
```
{
    "age": <PositiveInteger with value 5>
}
```
---

### How it all comes together:

Imagine a user has requested an operation which has a p-value threshold of 0.05. Thus, the POSTed payload contains, in part:
```
{
    ...
    "pval_threshold": 0.1
    ...
}
```

The view function gets the full `Operation` object. To access the expected inputs, we call
`Operation.inputs` which returns an instance of `OperationInputDict`. That looks like:
```
{
    ...
    "pval_threshold": <OperationInput>
    ...
}
```

We can then access the inputs individually like `myOperation.inputs['pval_threshold']` which returns that instance of `OperationInput`.

Drilling down further, `OperationInput` has various members like `name`, `description`, `spec`, etc. While the key is not present in the `operation_spec.json`, there is an implicit `value` which reflects the submitted input that a user might use. Until set by a user wishing
to run the tool, that value is None. Here, the user has submitted a value of 0.1.

Our instance of `OperationInput` has a `spec` member (i.e.`OperationInput.spec`) which returns an instance of `InputSpec`, a derived type of `InputOutputSpec`. `InputSpec` holds an instance of `Attribute`. However,
for the purposes of validation, we provide a method on the `OperationInput` class so we can verify submitted inputs.

