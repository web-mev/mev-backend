# This file contains information about the different table-
# based file types and methods for validating them
import logging
import re
import os
from functools import reduce

import pandas as pd
import numpy as np

from django.conf import settings
from django.core.paginator import Paginator, Page
from rest_framework.pagination import PageNumberPagination

from .base import DataResource, ParseException, UnexpectedTypeValidationException
from api.data_structures import Feature, \
    FeatureSet, \
    Observation, \
    ObservationSet, \
    create_attribute, \
    convert_dtype, \
    numeric_attribute_typenames
from api.utilities.basic_utils import alert_admins
from api.serializers.feature_set import FeatureSetSerializer
from api.serializers.observation_set import ObservationSetSerializer

logger = logging.getLogger(__name__)

# acceptable file extensions which give us a
# clue about how to parse the files.
CSV = 'csv'
TSV = 'tsv'
TAB = 'tab'
BED = 'bed'
VCF = 'vcf'
XLS = 'xls'
XLSX = 'xlsx'
TAB_DELIMITED_EXTENSIONS = [TSV, TAB, BED, VCF]
COMMA_DELIMITED_EXTENSIONS = [CSV]
EXCEL_EXTENSIONS = [XLS, XLSX]

class ParserNotFoundException(Exception):
    '''
    For raising exceptions when a proper 
    parser cannot be found.
    '''
    pass


# Some error messages:
PARSE_ERROR = ('There was an unexpected problem when'
    ' parsing and validating the file.')

PARSER_NOT_FOUND_ERROR = ('Could not find an appropriate parser'
    ' for the resource.  Please check the instructions.')

NON_NUMERIC_ERROR = 'The following columns contained non-numeric entries: {cols}'

NON_INTEGER_ERROR = 'The following columns contained non-integer entries: {cols}'

TRIVIAL_TABLE_ERROR = ('The file contained only a single column'
    ' which provided an index.  No data was provided in additional columns.')

BED_FORMAT_ERROR = ('When parsing the BED file, we detected issues with'
    ' column(s): {cols}. Note that BED files must NOT have column headers and can'
    ' contain only integers in the second and third columns, which correspond'
    ' to the start and end of a genomic location.  Please check your entries and'
    ' ensure your file does not have a header line.')

NUMBERED_COLUMN_NAMES_ERROR = ('All the column names were numbers.  Often this is due'
    ' to a missing column header.  In that case, there will be a missing row in'
    ' your table. If you named your columns with numbers, please change them'
    ' to something else to avoid incorrect parsing of the file.')

NUMBERED_ROW_NAMES_ERROR = ('All the row names were numbers.  We use the first column'
    ' to uniquely identify the rows for filtering purposes. If you named your rows with'
    ' numbers, please change them to something else (e.g. add "x" to the beginning'
    ' to avoid incorrect parsing of the file.')

NONUNIQUE_ROW_NAMES_ERROR = ('Your row names were not unique, which could cause'
    ' unexpected behavior.')

MISSING_HEADER_WARNING = ('One of your column names matched the values in the'
    ' corresponding problem.  This is not an error, but may indicate that a'
    ' proper header line was missing.  Please check to ensure the file was'
    ' parsed correctly.')

EMPTY_TABLE_ERROR = ('The parsed table was empty. If you are trying to'
    ' import an Excel spreadsheet, please ensure that the data is contained'
    ' in the first sheet of the workbook.')

def col_str_formatter(x):
    '''
    x is a tuple with the column number
    and column name
    '''
    return '%s (column %d)' % (x[0],x[1])


class TableResourcePage(Page):
    '''
    Overrides some methods of the django.core.paginator.Page
    class. The default version does a cast to a list, which is a problem
    when the "query set" is a dataframe instead of a QuerySet instance
    '''
    def __getitem__(self, index):
        if not isinstance(index, (int, slice)):
            raise TypeError(
                'Page indices must be integers or slices, not %s.'
                % type(index).__name__
            )

        return self.object_list[index]        


class TableResourcePaginator(Paginator):
    '''
    This overrides the default Django paginator, which
    typically expects to deal with a database query (a QuerySet).

    Dataframes are list-like (sort of...) but the problem is that
    the default django paginator ultimately does a cast to a list. When you 
    cast a pandas dataframe as a list, you only get a list of the
    column names, NOT a list of the "records" (rows).

    The django default Paginator mentions using the _get_page method as a
    way to override the django.core.paginator.Page class (which is where the
    cast occurs). By overriding that method, we can make our own Page-like
    class. 

    Finally, this class can be provided to a subclass of DRF's Paginator
    classes. 
    '''
    def _get_page(self, *args, **kwargs):
        '''
        Method to override the default behavior of the django core
        Paginator class. Should return a Page-like class. 
        '''
        return TableResourcePage(*args, **kwargs)


class TableResourcePageNumberPagination(PageNumberPagination):
    django_paginator_class = TableResourcePaginator
    page_size_query_param = settings.PAGE_SIZE_PARAM


class TableResource(DataResource):
    '''
    The `TableResource` is the most generic form of a delimited file.  Any
    type of data that can be represented as rows and columns.

    This or any of the more specific subclasses can be contained in files
    saved in CSV, TSV, or Excel (xls/xlsx) format.  If in Excel format, the 
    data of interest must reside in the first sheet of the workbook.

    Special tab-delimited files like BED or VCF files are recognized by
    their canonical extension (e.g. ".bed" or ".vcf").

    Note that unless you create a "specialized" implementation (e.g. like
    for a BED file), then we assume you have features as rows and observables
    as columns.
    '''
    ACCEPTABLE_EXTENSIONS = [
        CSV,
        TSV,
        TAB,
        BED,
        VCF,
        XLS,
        XLSX
    ]

    # the "standardized" format we will save all table-based files as:
    STANDARD_FORMAT = TSV

    def __init__(self):
        self.table = None

    @staticmethod
    def get_paginator():
        return TableResourcePageNumberPagination()

    @staticmethod
    def get_reader(resource_path):
        '''
        By using the file extension, we infer the delimiter
        Returns a pandas "reader" (e.g. `read_csv` or `read_table`)
        '''
        file_extension = DataResource.get_extension(resource_path)

        if file_extension in COMMA_DELIMITED_EXTENSIONS:
            return pd.read_csv
        elif file_extension in TAB_DELIMITED_EXTENSIONS:
            return pd.read_table
        elif file_extension in EXCEL_EXTENSIONS:
            return pd.read_excel
        else:
            logger.error('Could not infer the file format from the file'
            ' extension of {ext}.  Full resource path was {path}'.format(
                ext = file_extension,
                path = resource_path
            ))
            return None

    @staticmethod
    def index_all_numbers(names):
        '''
        Works for both row and column indexes.  Returns
        True if all the index labels are numbers.  
        '''
        if all([re.match('\d+', str(x)) for x in names]):
            return True
        else:
            return False

    def read_resource(self, resource_path):
        '''
        One common spot to define how the file is read
        '''
        reader = TableResource.get_reader(resource_path)
        if reader is None:
            raise ParserNotFoundException('')
        else:
            try:
                # read the table using the appropriate parser:
                self.table = reader(resource_path, index_col=0, comment='#')

                # call a method to 
            except Exception as ex:
                logger.info('Could not use {reader} to parse the file'
                ' at {path}'.format(
                    reader = reader,
                    path = resource_path
                ))     
                raise ParseException('Failed when parsing the table-based resource.')

    def performs_validation(self):
        '''
        Since we have methods to validate table-based DataResource types, we 
        override this method and return True, which indicates that we CAN
        perform validation.
        '''
        return True

    def validate_type(self, resource_path):
        '''
        In this base method, we determine attempt to parse the file.
        If there are no restrictions on content, succesful parsing
        of the file is good enough.

        More specific constraints on the file content are handled in child
        classes.  This method, however, fills in the `self.table` member
        which is then accessible to children.
        '''
        try:
            self.read_resource(resource_path)
            if self.table.shape == (0,0):
                return (False, EMPTY_TABLE_ERROR )

            if self.table.shape[1] == 0:
                return (False, TRIVIAL_TABLE_ERROR)

            # check if all the column names are numbers-- which would USUALLY
            # indicate a missing header
            columns_all_numbers = TableResource.index_all_numbers(self.table.columns)
            if columns_all_numbers:
                return (False, NUMBERED_COLUMN_NAMES_ERROR)

            # check if all the rownames are numbers, which would usually
            # indicate missing row names (i.e. a column of data is read
            # as the index)
            rows_all_numbers = TableResource.index_all_numbers(self.table.index)

            if rows_all_numbers:
                return (False, NUMBERED_ROW_NAMES_ERROR)

            # check for duplicate row names
            if self.table.index.has_duplicates:
                return (False, NONUNIQUE_ROW_NAMES_ERROR)
            return (True, None)

        except ParserNotFoundException as ex:
            return (False, PARSER_NOT_FOUND_ERROR)

        except ParseException as ex:
            return (False, PARSE_ERROR)
     
    def do_type_cast(self, v, typename):
        '''
        Used for casting the type when query params are provided.
        '''
        if typename in numeric_attribute_typenames:
            try:
                val = float(v)
            except ValueError as ex:
                raise ParseException('Could not parse "{v}" as a number.'.format(v=v))
        else:
            val = v 
        return val

    def perform_sorting(self, query_params):
        '''
        Sorts the table as requested. Sorts self.table in place

        A general sort string (after the equals sign) would be:
        <sort kw>:<col>,<sort kw>:<col>,...
        e.g. for sorting q-value (padj) ascending followed by fold-change descending, 
        [asc]:padj,[desc]:log2Foldchange
        '''
        if settings.SORT_PARAM in query_params:
            sort_strings = query_params[settings.SORT_PARAM].split(',')
            sort_order_list = []
            column_list = []
            for s in sort_strings:
                try:
                    sort_order, col = s.split(settings.QUERY_PARAM_DELIMITER)
                except ValueError:
                    raise ParseException('The sorting request was not properly formatted. '
                        'Please use "<ordering keyword>:<column name>"')
                if sort_order in settings.SORTING_OPTIONS:
                    sort_order_list.append(sort_order)
                else:
                    raise ParseException('The sort order "{s}" is not an available option. Choose from: {opts}'.format(
                        s = sort_order,
                        opts = ','.join(settings.SORTING_OPTIONS)
                    ))

                if col in self.table.columns:
                    column_list.append(col)
                else:
                    raise ParseException('The column identifier "{s}" does not exist in this resource. Options are: {opts}'.format(
                        s = col,
                        opts = ','.join(self.table.columns)
                    ))
            # at this point, all the sort orders and cols were OK. Now perform the sorting:
            # Need to convert our strings (e.g. "[asc]") to bools for the pandas sort_values method.
            order_bool = [True if x==settings.ASCENDING else False for x in sort_order_list]                
            self.table.sort_values(by=column_list, ascending=order_bool, inplace=True)

    def filter_against_query_params(self, query_params):
        '''
        Looks through the query params to subset the table
        '''
        table_cols = self.table.columns

        # since the pagination query params are among these, we DON'T
        # want to filter on them.
        ignored_params = [settings.PAGE_SIZE_PARAM, settings.PAGE_PARAM, settings.SORT_PARAM]

        # guard against some edge case where the table we are filtering happens to have 
        # columns that conflict with the pagination parameters. We simply inform the admins
        # and ignore that conflict by not using that filter
        if any([x in ignored_params for x in table_cols]):
            logger.warning('One of the column names conflicted with the pagination query params.')
            alert_admins()
        filters = []

        # used to map the pandas native type to a MEV-type so we can do type casting consistently
        type_dict = self.get_type_dict()
        for k,v in query_params.items():
            if (not k in ignored_params) and (k in table_cols):
                # v is either a value (in the case of strict equality)
                # or a delimited string which will dictate the comparison.
                # For example, to filter on the 'pval' column for values less than or equal to 0.01, 
                # v would be "[lte]:0.01". The "[lte]" string is set in our general settings file.
                split_v = v.split(settings.QUERY_PARAM_DELIMITER)
                column_type = type_dict[k] # gets a type name (as a string, e.g. "Float")
                if len(split_v) == 1:
                    # strict equality
                    val = self.do_type_cast(v, column_type)
                    try:
                        filters.append(self.table[k] == val)
                    except Exception as ex:
                        logger.error('Encountered exception!!')
                elif len(split_v) == 2:
                    val = self.do_type_cast(split_v[1], column_type)
                    try:
                        op = settings.OPERATOR_MAPPING[split_v[0]]
                    except KeyError as ex:
                        raise ParseException('The operator string ("{s}") was not understood. Choose'
                            ' from among: {vals}'.format(
                                s = split_v[0],
                                vals = ','.join(settings.OPERATOR_MAPPING.keys())
                            )
                        )
                    filters.append(
                        self.table[k].apply(lambda x: op(x, val))
                    )
                else:
                    raise ParseException('The query param string ({v}) for filtering on'
                        ' the {col} column was not formatted properly.'.format(
                            v = v,
                            col = k
                        )
                    )
            elif k in ignored_params:
                pass
            else:
                raise ParseException('The column "{c}" is not available for filtering.'.format(c=k))
        if len(filters) > 1:
            combined_filter = reduce(lambda x,y: x & y, filters)
            self.table = self.table.loc[combined_filter]
        elif len(filters) == 1:
            self.table = self.table.loc[filters[0]]

    def get_type_dict(self):
        '''
        Gets a mapping from the pandas native dtype to a MEV-compatible
        type.
        '''
        type_dict = {}
        for c in self.table.dtypes.index:
            # the convert_dtype function takes the native pandas dtype
            # and returns an attribute "type" that MEV understands.
            type_dict[c] = convert_dtype(str(self.table.dtypes[c]))
        return type_dict

    def replace_special_values(self):
        '''
        NaN and Inf values cause issues when we are serializing into JSON. If we have 
        an action/event that requires serialization of the table-based resource, then we
        should use this method to safely convert those values

        If there is any filtering involved (e.g. filtering for values greater than x)
        ensure you don't call this method first, as it will replace infinity values with
        strings and the filter won't work properly.
        '''
        self.table = self.table.replace({
            -np.infty: settings.NEGATIVE_INF_MARKER, 
            np.infty: settings.POSITIVE_INF_MARKER
        })
        self.table = self.table.mask(pd.isnull, None)

    def get_contents(self, resource_path, query_params={}):
        '''
        Returns a dataframe of the table contents

        The dataframe allows the caller to subset as needed to 'paginate'
        the rows of the table
        '''

        # use this function to convert the dataframe rows to our desired format
        def row_converter(row):
            return {'rowname': row.name, 'values': row.to_dict()}

        try:
            self.read_resource(resource_path)
            # if there were any filtering params requested, apply those
            self.filter_against_query_params(query_params)
            self.perform_sorting(query_params)
            self.replace_special_values()

            return self.table.apply(row_converter, axis=1).tolist()

        # for these first two exceptions, we already have logged
        # any problems when we called the `read_resource` method
        except ParserNotFoundException as ex:
            raise ex
        except ParseException as ex:
            raise ex
        # catch any other types of exceptions that we did not anticipate.
        except Exception as ex:
            logger.error('An unexpected error occurred when preparing'
                ' a resource preview for the resource at {path}. Exception'
                ' was: {ex}'.format(
                    path=resource_path,
                    ex=ex
                ))
            raise ex

    def extract_metadata(self, resource_path, parent_op_pk=None):
        '''
        This method extracts metadata from the Resource in question and 
        saves it to the database.

        In the case of new Resources being added, the `parent_op` is None
        since no MEV-based analyses were responsible for the creation of the 
        Resource.  If the Resource is created by some MEV-based analysis,
        the primary-key for that ExecutedOperation will be passed.

        '''
        logger.info('Extracting metadata from resource with path ({path}).'.format(
            path = resource_path
        ))

        # If the self.table field was not already filled, we need to 
        # read the data
        if self.table is None:
            logger.info('Resource with path ({path}) was not '
                'previously parsed.  Do that now.'.format(
                    path=resource_path
                )
            )
            is_valid, message = self.validate_type(resource_path)
            if not is_valid:
                raise UnexpectedTypeValidationException(message)

        # now we have a table loaded at self.table.  

        # call the super method to initialize the self.metadata
        # dictionary
        super().setup_metadata()

        # now add the information to self.metadata:
        if parent_op_pk:
            self.metadata[DataResource.PARENT_OP] = parent_op_pk

    def save_in_standardized_format(self, resource_path, resource_name):
        '''
        To avoid all the analyses having to concern themselves with data formats
        like csv, tsv, xlsx, etc. we just save table-based formats as a TSV.
        '''
        logger.info('Saving resource with path ({path}) to the standard format.'
            ' for a table-based resource'.format(
            path = resource_path
        ))

        # If the self.table field was not already filled, we need to 
        # read the data
        if self.table is None:
            logger.info('Resource with path ({path}) was not '
                'previously parsed.  Do that now.'.format(
                    path=resource_path
                )
            )
            try:
                # this call will set the self.table member
                self.read_resource(resource_path)
            except Exception as ex:
                logger.error('Failed when trying to save in standard format.'
                    ' Specifically, failed when reading the resource, as self.table'
                    ' was None. Path of resource was: {path}'.format(
                        path=resource_path
                    )
                )
        # ok, self.table is set-- save it.
        current_file_extension = DataResource.get_extension(resource_path)
        file_dir =  os.path.dirname(resource_path)
        basename = os.path.basename(resource_path)
        basename_contents = basename.split('.')
        basename_contents[-1] = self.STANDARD_FORMAT
        new_basename = '.'.join(basename_contents)
        new_path = os.path.join(file_dir, new_basename)

        name_contents = resource_name.split('.')
        name_contents[-1] = self.STANDARD_FORMAT
        new_name = '.'.join(name_contents)

        logger.info('Writing the reformatted table-based resource to: {p}.'
            ' The new name is {n}.'.format(
            p = new_path,
            n = new_name
        ))
        self.table.to_csv(new_path, sep='\t')
        return new_path, new_name   

class Matrix(TableResource):
    '''
    A `Matrix` is a delimited table-based file that has only numeric types.
    These types can be mixed, like floats and integers
    '''
    ACCEPTABLE_EXTENSIONS = [
        CSV,
        TSV,
        TAB,
        XLS,
        XLSX
    ]

    DESCRIPTION = 'A table of where all the entries are numbers'\
        ' except the first column (which names the rows) and the' \
        ' first line (which gives the column names). The cell at the' \
        ' first row and column may be left blank.'

    # looking for integers OR floats.  Both are acceptable  
    TARGET_PATTERN = '(float|int)\d{0,2}'

    def check_column_types(self, target_pattern):
        '''
        Checks each column against a specific numpy/pandas dtype.
        The specific dtype comes from the class member.
        '''
        problem_columns = []
        for i,col in enumerate(self.table.dtypes):
            if not re.match(target_pattern, str(col)):
                colname = self.table.columns[i]
                problem_columns.append(
                    (colname, i+1)
                )
        return problem_columns


    def validate_type(self, resource_path):
        is_valid, error_msg = super().validate_type(resource_path)
        if not is_valid:
            return (False, error_msg)

        # was able to at least open/parse the file.
        # now check for numeric types
        problem_columns = self.check_column_types(Matrix.TARGET_PATTERN)

        if len(problem_columns) > 0:
            col_str = ', '.join([col_str_formatter(x) for x in problem_columns])
            error_message = NON_NUMERIC_ERROR.format(cols=col_str)
            return (False, error_message)

        return (True, None)

    def extract_metadata(self, resource_path, parent_op_pk=None):

        super().extract_metadata(resource_path, parent_op_pk)

        # the FeatureSet comes from the rows:
        f_set = FeatureSet([Feature(x) for x in self.table.index])
        self.metadata[DataResource.FEATURE_SET] = FeatureSetSerializer(f_set).data

        # the ObservationSet comes from the cols:
        o_set = ObservationSet([Observation(x) for x in self.table.columns])
        self.metadata[DataResource.OBSERVATION_SET] = ObservationSetSerializer(o_set).data
        return self.metadata


class IntegerMatrix(Matrix):
    '''
    An `IntegerMatrix` further specializes the `Matrix`
    to admit only integers.
    '''
    # looking for only integers. 
    TARGET_PATTERN = 'int\d{0,2}'

    DESCRIPTION = 'A table of where all the entries are integers'\
        ' except the first column (which names the rows) and the' \
        ' first line (which gives the column names). The cell at the' \
        ' first row and column may be left blank.'

    def validate_type(self, resource_path):

        # first check that it has all numeric types.  If that fails
        # immediately return--
        is_valid, error_message = super().validate_type(resource_path)
        if not is_valid:
            return (False, error_message)

        # was valid for numeric types.  Now check for integer
        problem_columns = self.check_column_types(IntegerMatrix.TARGET_PATTERN)
        if len(problem_columns) > 0:

            # one problem with pandas is that NaN values cause a column
            # to be parsed as a float, even if all other values in the 
            # column are integers.  We can do a secondary check, however, 
            # to see if the remaining values (non-NaN) are basically
            # integers.  We check if the numbers look like "2.0".
            # If that is the case, we remove that column from the 
            # "problem columns".  
            for i,c in enumerate(problem_columns):
                # recall c is a tuple of (colname, col number)
                if all([
                        re.match('\d+\.0', str(x)) 
                        for x in self.table[c[0]].dropna()]):
                    problem_columns.pop(i)

            # if there are still any remaining problematic cols,
            # we now issue an error
            if len(problem_columns) > 0:
                col_str = ', '.join([col_str_formatter(x) for x in problem_columns])
                error_message = NON_INTEGER_ERROR.format(cols=col_str)
                return (False, error_message)
            
        return (True, None)

class RnaSeqCountMatrix(IntegerMatrix):
    '''
    A very-explicit class (mainly for making things user-friendly)
    where we provide specialized behavior/messages specific to count matrices
    generated from RNA-seq data
    '''
    DESCRIPTION = 'A table of integer-based counts corresponding to'\
        ' the number of sequencing reads associated with a particular' \
        ' gene or transcript.'


class ElementTable(TableResource):
    '''
    An ElementTable captures common behavior of tables which
    annotate Observations (AnnotationTable) or Features (FeatureTable)

    It's effectively an abstract class-- 
    '''

    ACCEPTABLE_EXTENSIONS = [
        CSV,
        TSV,
        TAB,
        XLS,
        XLSX
    ]

    def validate_type(self, resource_path):

        # check that file can be parsed:
        is_valid, error_message = super().validate_type(resource_path)
        if not is_valid:
            return (False, error_message)
        
        # check that the file is "useful" in that it has
        # more than one column.  It's not REALLY an error, but it does not 
        # provide any information.  This can also be caught earlier, but
        # we provide it here just as a secondary guard.
        if self.table.shape[1] == 0:
            return (False, TRIVIAL_TABLE_ERROR)
        return (True, None)

    def prep_metadata(self, element_class):
        '''
        When we extract the metadata from an ElementTable, we 
        expect the Element instances (Observations or Features) 
        to be contained in the rows.  

        Additional columns specify attributes which we incorporate.

        The `element_class` arg is a class which implements the specific
        type we want (i.e. Observation or Feature)
        '''
        # Go through the columns and find out the primitive types
        # for each column/covariate.
        # Note that we can't determine specific types (e.g. bounded integers)
        # from general annotations.  We basically allow floats, integers, and
        # "other" types, which get converted to strings.
        type_dict = self.get_type_dict()

        # convert NaN and infs to our special marker values
        self.replace_special_values()

        element_list = []
        for id, row_series in self.table.iterrows():
            d = row_series.to_dict()
            attr_dict = {}
            for key, val in d.items():
                # Note the 'allow_null=True', so that attributes can be properly serialized
                # if they are missing a value. This happens, for instance, in FeatureTable
                # instances where p-values were not assigned.
                attr = create_attribute(key,
                    {
                        'attribute_type': type_dict[key],
                        'value': val
                    },
                    allow_null=True
                )
                attr_dict[key] = attr
            element_list.append(element_class(id, attr_dict))
        return element_list


class AnnotationTable(ElementTable):
    '''
    An `AnnotationTable` is a special type of table that will be responsible
    for annotating Observations/samples (e.g. adding sample names and 
    associated attributes like experimental group or other covariates)

    The first column will give the sample names and the remaining columns will
    each individually represent different covariates associated with that sample.
    '''

    DESCRIPTION = 'This type of file is used to add metadata to your samples.' \
        ' The first column has the sample name and the remaining columns contain' \
        ' metadata about each sample (for instance, experimental group,'\
        ' treatment, or similar.'

    def validate_type(self, resource_path):

        # check that file can be parsed:
        is_valid, error_message = super().validate_type(resource_path)
        if not is_valid:
            return (False, error_message)

        # it is hard to check for proper headers for annotation
        # files since they have relatively free format.  However,
        # if the column name matches any values in its column, the
        # annotation was likely missing a header line.  For example,
        # >>> df
        # SW1_Control   CTRL
        # 0  SW2_Control   CTRL
        # 1  SW3_Control   CTRL
        # 2  SW4_Treated  TREAT
        # 3  SW5_Treated  TREAT
        # 4  SW6_Treated  TREAT
        #
        # Here, "CTRL" becomes the header, but it's clearly 
        # just due to a missing header.  We don't issue an 
        # error, but we do warn the user by adding a comment.
        flagged_columns = []
        for c in self.table.columns:
            if np.sum(c == self.table[c]) > 0:
                flagged_columns.append(c)
        if len(flagged_columns) > 0:
            return (True, MISSING_HEADER_WARNING)

        return (True, None)

    def extract_metadata(self, resource_path, parent_op_pk=None):
        '''
        When we extract the metadata from an AnnotationTable, we 
        expect the Observation instances to be the rows.  

        Additional columns specify attributes of each Observation,
        which we incorporate
        '''
        super().extract_metadata(resource_path, parent_op_pk)

        observation_list = super().prep_metadata(Observation)
        o_set = ObservationSet(observation_list)
        self.metadata[DataResource.OBSERVATION_SET] = ObservationSetSerializer(o_set).data
        return self.metadata


class FeatureTable(ElementTable):
    '''
    A `FeatureTable` is a type of table that has aggregate information about
    the features, but does not have any "observations" in the columns.  An example
    would be the results of a differential expression analysis.  Each row corresponds
    to a gene (feature) and the columns are information about that gene (such as p-value).

    Another example could be a table of metadata about genes (e.g. pathways or perhaps a 
    mapping to a different gene identifier).

    The first column will give the feature/gene identifiers and the remaining columns will
    have information about that gene
    '''

    DESCRIPTION = 'This type of file describes the "features" of your data.  In the genomics' \
        ' context, one example of a feature is a gene.  Therefore, you could use this table' \
        ' to give additional information about each gene, such as alternative symbols,' \
        ' oncogene status, or similar.  Each row contains information about a single gene.' \
        ' Note, however, that this concept is completely general and not restricted' \
        ' to information about genes or transcripts.'

    def extract_metadata(self, resource_path, parent_op_pk=None):
        '''
        When we extract the metadata from a FeatureTable, we 
        expect the Feature instances to be the rows.  

        Additional columns specify attributes of each Feature,
        which we incorporate
        '''
        super().extract_metadata(resource_path, parent_op_pk)

        feature_list = super().prep_metadata(Feature)
        f_set = FeatureSet(feature_list)
        self.metadata[DataResource.FEATURE_SET] = FeatureSetSerializer(f_set).data
        return self.metadata


class BEDFile(TableResource):
    '''
    A file format that corresponds to the BED format.  This is
    the minimal BED format, which has:

    - chromosome
    - start position
    - end position

    Additional columns are ignored.

    By default, BED files do NOT contain headers and we enforce that here.
    '''

    DESCRIPTION = 'A three-column BED-format file'

    ACCEPTABLE_EXTENSIONS = [BED,]
    
    def validate_type(self, resource_path):
        reader = TableResource.get_reader(resource_path)

        # if the BED file has a header, the reader below will incorporate
        # that into the columns and the 2nd and 3rd columns will no longer have
        # the proper integer type.
        table = reader(resource_path, 
            names=['chrom','start','stop'],
            usecols=[0,1,2])
        start_col_int = re.match('int\d{0,2}', str(table['start'].dtype))
        stop_col_int = re.match('int\d{0,2}', str(table['stop'].dtype))
        if start_col_int and stop_col_int:
            return (True, None)
        else:
            problem_columns = []
            if start_col_int is None:
                problem_columns.append(2)
            if stop_col_int is None:
                problem_columns.append(3)

            cols = ','.join([str(x) for x in problem_columns])
            error_message = BED_FORMAT_ERROR.format(cols=cols)
            return (False, error_message)

    def extract_metadata(self, resource_path, parent_op_pk=None):
        super().extract_metadata(resource_path, parent_op_pk)
        return self.metadata
