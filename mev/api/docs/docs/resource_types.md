### Resource types

A `Resource` represents some generic notion of data and its `resource_type` field/member is a string identifier that identifies the specific format of the data.

The string identifiers map to concrete classes that implement validation methods for the `Resource`.  When a new `Resource` is added (via upload or directly by an admin via the API), the validation method is called.  Similarly, if a user tries to change the `resource_type`, it will trigger the validation process.

Current `resource_types` fall into two broad categories:

- Table-based formats
- Sequence-based formats

Table-based formats are any array-like format, such as a typical CSV file.  This covers a wide variety of standard formats encountered in computational biology, including GTF annotation files and BED files.  The primitive data types contained in each column are determined using Python's Pandas library, which refers to these as "dtypes"; for example, a column identified as `int64` certainly qualifies as an integer type.  If the column contains any non-integers (but all numbers), Pandas automatically converts it to a float type (e.g. `float64`) which allows us to easily validate the content of each column.  

Sequence-based formats are formats like FastQ, Fasta, or SAM/BAM. 

#### Table-based resource types

::: resource_types.table_types.TableResource
    :docstring:


::: resource_types.table_types.Matrix
    :docstring:


::: resource_types.table_types.IntegerMatrix
    :docstring:


::: resource_types.table_types.AnnotationTable
    :docstring:

For example, if we received the following table:

| sample | genotype | treatment |
|-|-|-|
| A | WT | Y |
| B | WT | N |

Then this table can be used to create `Attribute`s which can be added to
the `Observation`s.  After the annotations are uploaded, the users must tell MEV how to interpret the columns (e.g. as a string?  as a bounded float?), but once that type is specified, we can validate the annotations against that choice and subsequently add the `Attribute`s to the `Observation`s. 

::: resource_types.table_types.BEDFile
    :docstring:

#### Sequence-based formats

::: resource_types.sequence_types.SequenceResource
    :docstring:

::: resource_types.sequence_types.FastAResource
    :docstring:

::: resource_types.sequence_types.FastQResource
    :docstring:

::: resource_types.sequence_types.AlignedSequenceResource
    :docstring: