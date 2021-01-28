### Resource types

A `Resource` represents some generic notion of data and its `resource_type` field/member is a string identifier that identifies the specific format of the data. Resource types allow us to specify the format of input/output files of `Operation`s. Therefore, we can predictably present options for those inputs and allow `Resource`s to flow from one analysis to another.

The string identifiers map to concrete classes that implement validation methods for the `Resource`.  For example, the string `I_MTX` indicates that the `Resource` is an integer matrix. When a new `Resource` is added (via upload or directly by an admin via the API), the validation method is called.  Similarly, if a user tries to change the `resource_type`, it will trigger the validation process.

Current `resource_types` fall into several broad categories:

- Table-based formats
- Sequence-based formats
- JSON
- General. Not a true type, but rather denotes that a better, more specific type cannot be specified.

**Table-based formats**

Table-based formats are any matrix-like format, such as a typical CSV file.  In addition to being a common file format for expression matrices and similar experimental data, this covers a wide variety of standard formats encountered in computational biology, including GTF annotation files and BED files.

Specific types are shown below in the auto-generated documentation, but we touch on some of the more general descriptions immediately below.

During validation, the primitive data types contained in each column are determined using Python's Pandas library, which refers to these as "dtypes"; for example, a column identified as `int64` certainly qualifies as an integer type.  If the column contains any non-integers (but all numbers), Pandas automatically converts it to a float type (e.g. `float64`) which allows us to easily validate the content of each column. 

We enforce that specific sub-types of this general table-based format adhere to our expectations. For instance, an expression matrix requires a first row which contains samples/observation names. Furthermore, the first column should correspond to gene identifiers (`Feature`s more generally). While we cannot exhaustively validate every file, we make certain reasonable assumptions. For example, if the first row is all numbers, we assume that a header is missing. Certainly one *could* name their samples with numeric identifiers, but we enforce that they need to be strings. Failure to conform to these expectations will result in the file failing to validate. Users should be informed of the failure with a helpful message for resolution.

Also note that while the user may submit files in a format such as CSV, we internally convert to a common format (e.g. TSV) so that downstream tools can avoid having to include multiple file-parsing schemes.

Since table-based formats naturally lend themselves to arrays of atomic items (i.e. each row as a "record"), the contents of table-based formats can be requested in a paginated manner via the API.

**Sequence-based formats**

Sequence-based formats are formats like FastQ, Fasta, or SAM/BAM. These types of files cannot reasonably be validated up front, so any `Operation`s which use these should plan on gracefully handling problems with their format.

**JSON**

For data that is not easily represented in a table-based format, we retain JSON as a general format. We use Python's internal `json` library to enforce the format of these files. Any failure to parse the file results in a validation error. 

Note that the contents of array-based JSON files can be paginated, but general JSON objected-based resources cannot. An example of the former is:
```
[
    {
        "keyA": 1,
        "some_value": "abc"
    },
    ...
    {
        "keyA": 8,
        "some_value": "xyz"
    }
]
```
These can be paginated so that each internal "object" (e.g. `{"keyA": 1,"some_value":"abc"}`) is a record. 

**General**

Generally this format should be avoided as it allows un-validated/unrestricted data formats to be passed around. However, for certain types (such as a tarball of many files), we sometimes have no other reasonable option.

#### Table-based resource types

::: resource_types.table_types.TableResource
    :docstring:


::: resource_types.table_types.Matrix
    :docstring:


::: resource_types.table_types.IntegerMatrix
    :docstring:

::: resource_types.table_types.RnaSeqCountMatrix
    :docstring:

::: resource_types.table_types.ElementTable
    :docstring:

::: resource_types.table_types.AnnotationTable
    :docstring:

For example, if we received the following table:

| sample | genotype | treatment |
|-|-|-|
| A | WT | Y |
| B | WT | N |

Then this table can be used to add `Attribute`s  to the corresponding `Observation`s. Note that the backend doesn't manage this. Instead, the front-end will be responsible for taking the `AnnotationTable` and creating/modifying `Observation`s.

::: resource_types.table_types.FeatureTable
    :docstring:

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