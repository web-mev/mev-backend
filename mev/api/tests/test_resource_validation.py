import unittest
import os

import pandas as pd
from resource_types.table_types import TableResource, \
    Matrix, \
    IntegerMatrix, \
    AnnotationTable, \
    BEDFile, \
    PARSE_ERROR, \
    PARSER_NOT_FOUND_ERROR, \
    NON_NUMERIC_ERROR, \
    NON_INTEGER_ERROR, \
    TRIVIAL_TABLE_ERROR, \
    BED_FORMAT_ERROR, \
    NUMBERED_COLUMN_NAMES_ERROR, \
    NUMBERED_ROW_NAMES_ERROR, \
    NONUNIQUE_ROW_NAMES_ERROR, \
    MISSING_HEADER_WARNING, \
    EMPTY_TABLE_ERROR

# the api/tests dir
TESTDIR = os.path.dirname(__file__)
TESTDIR = os.path.join(TESTDIR, 'resource_validation_test_files')

class TestBasicTable(unittest.TestCase):

    def test_reader_type(self):
        '''
        Is able to return the correct parser for the file extension

        Note that none of the paths below actually have to exist.  
        The method is just examining the file extension.
        '''
        t = TableResource()
        reader = t.get_reader('test_general_table.tsv', 'tsv')
        self.assertEqual(reader, pd.read_table)

        reader = t.get_reader('test_integer_matrix.csv', 'csv')
        self.assertEqual(reader, pd.read_csv)

        reader = t.get_reader('test_integer_matrix.CSV', 'csv')
        self.assertEqual(reader, pd.read_csv)       

        reader = t.get_reader('example_bed.bed', 'bed')
        self.assertEqual(reader, pd.read_table)

        reader = t.get_reader('something.xls', 'xls')
        self.assertEqual(reader, pd.read_excel)

        reader = t.get_reader('junk.abc', 'abc')
        self.assertIsNone(reader)

        reader = t.get_reader('junk.odc', 'odc')
        self.assertIsNone(reader)

    def test_fails_at_empty_table(self):
        '''
        If the file is literally empty, check that it fails
        '''
        t = TableResource()
        is_valid, err = t.validate_type(os.path.join(
            TESTDIR, 'test_empty.tsv'), 'tsv')
        self.assertFalse(is_valid)
        self.assertEqual(err, PARSE_ERROR)
        
    def test_reads_basic_table(self):
        '''
        Is able to parse and report validation on a well-formatted
        general table.
        '''
        t = TableResource()
        is_valid, err = t.validate_type(os.path.join(
            TESTDIR, 'test_general_table.tsv'), 'tsv')
        self.assertTrue(is_valid)
        self.assertIsNone(err)

    def test_reports_unknown_parser(self):
        t = TableResource()
        is_valid, err = t.validate_type(os.path.join(
            TESTDIR, 'something.abc'), 'abc')
        self.assertFalse(is_valid)
        self.assertEqual(err, PARSER_NOT_FOUND_ERROR) 

    def test_fails_malformatted_basic_table(self):
        t = TableResource()
        is_valid, err = t.validate_type(os.path.join(
            TESTDIR, 'test_malformatted_table.tsv'), 'tsv')
        self.assertFalse(is_valid)
        self.assertEqual(err, PARSE_ERROR)

    def test_handles_comment_headerlines_appropriately(self):
        t = TableResource()
        is_valid, err = t.validate_type(os.path.join(
            TESTDIR, 'test_general_table.with_comment.tsv'), 'tsv')
        self.assertTrue(is_valid)
        self.assertIsNone(err)


class TestMatrix(unittest.TestCase):
    '''
    Tests tables where all entries must be numeric
    (float or int)
    '''

    def test_reads_float_table(self):
        '''
        Capable of parsing a table of mixed numeric types
        '''
        m = Matrix()
        is_valid, err = m.validate_type(os.path.join(
            TESTDIR, 'test_matrix.tsv'), 'tsv')
        self.assertTrue(is_valid)
        self.assertIsNone(err) 

    def test_reads_integer_table(self):
        '''
        Tables of integers also pass validation
        '''
        m = Matrix()
        is_valid, err = m.validate_type(os.path.join(
            TESTDIR, 'test_integer_matrix.tsv'), 'tsv')
        self.assertTrue(is_valid)
        self.assertIsNone(err) 

    def test_reads_table_without_gene_label(self):
        '''
        Tables with a blank first column name are OK
        '''
        m = Matrix()
        is_valid, err = m.validate_type(os.path.join(
            TESTDIR, 'test_integer_matrix.no_gene_label.tsv'), 'tsv')
        self.assertTrue(is_valid)
        self.assertIsNone(err) 

    def test_incorrect_table(self):
        '''
        Tests that a table with a string entry fails
        '''
        m = Matrix()
        is_valid, err = m.validate_type(os.path.join(
            TESTDIR, 'test_incorrect_matrix.tsv'), 'tsv')
        self.assertFalse(is_valid)
        bad_col_str = 'SW2_Control (column 2)'
        expected_err_str = NON_NUMERIC_ERROR.format(cols=bad_col_str)
        self.assertEqual(err, expected_err_str) 

    def test_table_without_header(self):
        '''
        Tables without a header row fail
        '''
        m = Matrix()
        is_valid, err = m.validate_type(os.path.join(
            TESTDIR, 'test_integer_matrix.no_header.tsv'), 'tsv')
        self.assertFalse(is_valid)
        self.assertEqual(err, NUMBERED_COLUMN_NAMES_ERROR)

    def test_table_without_rownames(self):
        '''
        Tables without row names fails
        '''
        m = Matrix()
        is_valid, err = m.validate_type(os.path.join(
            TESTDIR, 'test_integer_matrix.no_rownames.tsv'), 'tsv')
        self.assertFalse(is_valid)
        self.assertEqual(err, NUMBERED_ROW_NAMES_ERROR)

    def test_duplicate_rownames_fails(self):
        m = Matrix()
        is_valid, err = m.validate_type(os.path.join(
            TESTDIR, 'test_matrix.duplicate_rownames.tsv'), 'tsv')
        self.assertFalse(is_valid)
        self.assertEqual(err, NONUNIQUE_ROW_NAMES_ERROR)

    def test_reads_float_table_with_na(self):
        '''
        Capable of parsing a table containing missing
        data
        '''
        m = Matrix()
        is_valid, err = m.validate_type(os.path.join(
            TESTDIR, 'test_matrix.with_na.tsv'), 'tsv')
        self.assertTrue(is_valid)
        self.assertIsNone(err) 



class TestIntegerMatrix(unittest.TestCase):


    def test_fails_with_float_table(self):
        '''
        Capable of parsing a table of mixed numeric types
        '''
        m = IntegerMatrix()
        is_valid, err = m.validate_type(os.path.join(
            TESTDIR, 'test_matrix.tsv'), 'tsv')
        self.assertFalse(is_valid)

    def test_reads_integer_table(self):
        '''
        Tables of integers pass validation
        '''
        m = IntegerMatrix()
        is_valid, err = m.validate_type(os.path.join(
            TESTDIR, 'test_integer_matrix.tsv'), 'tsv')
        self.assertTrue(is_valid)
        self.assertIsNone(err) 

        m = IntegerMatrix()
        is_valid, err = m.validate_type(os.path.join(
            TESTDIR, 'test_integer_matrix.csv'), 'csv')
        self.assertTrue(is_valid)
        self.assertIsNone(err) 

    def test_table_without_header(self):
        '''
        Tables without a header row fail
        '''
        m = IntegerMatrix()
        is_valid, err = m.validate_type(os.path.join(
            TESTDIR, 'test_integer_matrix.no_header.tsv'), 'tsv')
        self.assertFalse(is_valid)
        self.assertEqual(err, NUMBERED_COLUMN_NAMES_ERROR)

    def test_reads_table_without_gene_label(self):
        '''
        Tables with a blank first column name are OK
        '''
        m = IntegerMatrix()
        is_valid, err = m.validate_type(os.path.join(
            TESTDIR, 'test_integer_matrix.no_gene_label.tsv'), 'tsv')
        self.assertTrue(is_valid)
        self.assertIsNone(err) 

    def test_table_without_rownames(self):
        '''
        Tables without row names fails
        '''
        m = IntegerMatrix()
        is_valid, err = m.validate_type(os.path.join(
            TESTDIR, 'test_integer_matrix.no_rownames.tsv'), 'tsv')
        self.assertFalse(is_valid)
        self.assertEqual(err, NUMBERED_ROW_NAMES_ERROR)

    def test_duplicate_rownames_fails(self):
        m = IntegerMatrix()
        is_valid, err = m.validate_type(os.path.join(
            TESTDIR, 'test_matrix.duplicate_rownames.tsv'), 'tsv')
        self.assertFalse(is_valid)
        self.assertEqual(err, NONUNIQUE_ROW_NAMES_ERROR)

    def test_reads_int_table_with_na(self):
        '''
        Capable of parsing an integer table containing missing
        data.  Note that this requires some special handling
        since NaN's force the column to be parsed as a float,
        even if all other values in the column are integers
        '''
        m = IntegerMatrix()
        is_valid, err = m.validate_type(os.path.join(
            TESTDIR, 'test_integer_matrix.with_na.csv'), 'csv')
        self.assertTrue(is_valid)
        self.assertIsNone(err) 

    def test_fails_parsing_int_table_with_na(self):
        '''
        Here, we take a NaN value which would be typically handled
        gracefully as in the TestIntegerMatrix.test_reads_int_table_with_na
        test function above.  However, we also put a non-integer in the same
        column to test that the special case handling is working properly.
        '''
        m = IntegerMatrix()
        is_valid, err = m.validate_type(os.path.join(
            TESTDIR, 'test_integer_matrix.with_na_and_float.csv'), 'csv')
        self.assertFalse(is_valid)

    def test_fails_parsing_int_table_with_na_and_float(self):
        '''
        Here, we take a NaN value which would be typically handled
        gracefully as in the TestIntegerMatrix.test_reads_int_table_with_na
        test function above.  However, we also put a non-integer in a
        different column (5) to test that the special case handling is 
        working properly.
        '''
        m = IntegerMatrix()
        is_valid, err = m.validate_type(os.path.join(
            TESTDIR, 'test_integer_matrix.with_multiple_na_and_float.csv'), 'csv')
        self.assertFalse(is_valid)
        bad_col_str = 'SW5_Treated (column 5)'
        expected_err_str = NON_INTEGER_ERROR.format(cols=bad_col_str)
        self.assertEqual(err, expected_err_str) 

    def test_excel_parses_correctly(self):
        '''
        Test that we can parse an excel spreadsheet provided the 
        data is contained in the first sheet
        '''
        m = IntegerMatrix()
        is_valid, err = m.validate_type(os.path.join(
            TESTDIR, 'test_integer_matrix.xlsx'), 'xlsx')
        self.assertTrue(is_valid)

    def test_excel_fails_if_not_in_first_sheet(self):
        '''
        If the data is contained on a different sheet than "the first"
        the table is empty.  If the first sheet contained data, then 
        there's really nothing we can do to correct that.
        '''
        m = IntegerMatrix()
        is_valid, err = m.validate_type(os.path.join(
            TESTDIR, 'test_integer_matrix.second_sheet.xlsx'), 'xlsx')
        self.assertFalse(is_valid)
        self.assertEqual(err, EMPTY_TABLE_ERROR)

    def test_fails_if_filetype_incorrect(self):
        '''
        If a user specifies CSV but the file is, in fact,
        a TSV, we fail out.

        We are unable to decipher (without looking at the table)
        that it was due to an incorrect file extension, but the
        file still fails validation.
        '''
        m = IntegerMatrix()
        is_valid, err = m.validate_type(os.path.join(
            TESTDIR, 'test_tsv_integer_matrix_labeled_as_csv.csv'), 'csv')
        self.assertFalse(is_valid)

    def test_fails_if_filetype_incorrect_case2(self):
        '''
        If a user specifies TSV but the file is, in fact,
        a CSV, we fail out.

        We are unable to decipher (without looking at the table)
        that it was due to an incorrect file extension, but the
        file still fails validation.
        '''
        m = IntegerMatrix()
        is_valid, err = m.validate_type(os.path.join(
            TESTDIR, 'test_csv_integer_matrix_labeled_as_tsv.tsv'), 'tsv')
        self.assertFalse(is_valid)


class TestAnnotationMatrix(unittest.TestCase):

    def test_table_without_header(self):
        '''
        Tables without a header row pass, but get warned
        if there are duplicate values
        '''
        t = AnnotationTable()
        is_valid, msg = t.validate_type(os.path.join(
            TESTDIR, 'test_annotation.no_header.tsv'), 'tsv')
        self.assertTrue(is_valid)
        self.assertEqual(msg, MISSING_HEADER_WARNING)

    def test_table_with_extra_columns_and_extra_row(self):
        '''
        The table we test here has extra rows and columns. Common for XLS exports.
        Should NOT fail this since it's common and would be hard for frontend
        users to diagnose
        '''
        t = AnnotationTable()
        p = os.path.join(TESTDIR, 'annotation_with_extra_cols_and_rows.csv')
        is_valid, msg = t.validate_type(p, 'csv')
        self.assertTrue(is_valid)
        metadata = t.extract_metadata(p, 'csv')

    def test_table_with_single_column_fails(self):
        '''
        Tables with only a single column fails since
        it is not useful
        '''
        t = AnnotationTable()
        is_valid, err = t.validate_type(os.path.join(
            TESTDIR, 'single_column_annotation.tsv'), 'tsv')
        self.assertFalse(is_valid)
        self.assertEqual(err, EMPTY_TABLE_ERROR)

    def test_duplicate_rownames_fails(self):
        '''
        Cannot have more than one annotation per 'sample'
        '''
        t = AnnotationTable()
        is_valid, err = t.validate_type(
            os.path.join(TESTDIR, 'two_column_annotation.duplicate_rows.tsv'),
            'tsv'
        )
        self.assertFalse(is_valid)
        self.assertEqual(err, NONUNIQUE_ROW_NAMES_ERROR)

    def test_parses_proper_annotations(self):
        t = AnnotationTable()
        is_valid, err = t.validate_type(os.path.join(
            TESTDIR, 'two_column_annotation.tsv'), 'tsv')
        self.assertTrue(is_valid)
        self.assertIsNone(err)

    def test_parses_compliant_table_with_uncompliant_attribute(self):
        '''
        In this test, we have the case where a user submits an annotation file
        which has a column of strings. One of those strings, however, is entirely
        numeric. That is accepted, however, as there are situations where annotations
        could be presented in this manner.
        '''
        t = AnnotationTable()
        p = os.path.join(
            TESTDIR, 'test_annotation_with_noncompliant_str.tsv')
        is_valid, err = t.validate_type(p, 'tsv')
        self.assertTrue(is_valid)
        self.assertIsNone(err)
        metadata = t.extract_metadata(p, 'tsv')

class TestBed(unittest.TestCase):

    def test_bed_without_header_fails(self):
        '''
        Technically, BED format does not allow a header.  
        Since BED files may feed into downstream processes, we 
        reject these malformatted BED files
        '''
        b = BEDFile()
        is_valid, err = b.validate_type(os.path.join(
            TESTDIR, 'bed_with_header.bed'), 'bed')
        self.assertFalse(is_valid)
        self.assertEqual(err, BED_FORMAT_ERROR.format(cols='2,3'))


    def test_bed_with_extra_fields_passes(self):
        '''
        This allows some of the extended BED formats.
        '''
        b = BEDFile()
        is_valid, err = b.validate_type(os.path.join(
            TESTDIR, 'five_column.bed'), 'bed')
        self.assertTrue(is_valid)


