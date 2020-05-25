import unittest
import os

import pandas as pd
from api.resource_types.table_types import TableResource, \
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
    MISSING_HEADER_WARNING

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
        reader = t.get_reader('test_general_table.tsv')
        self.assertEqual(reader, pd.read_table)

        reader = t.get_reader('test_integer_matrix.csv')
        self.assertEqual(reader, pd.read_csv)

        reader = t.get_reader('test_integer_matrix.CSV')
        self.assertEqual(reader, pd.read_csv)       

        reader = t.get_reader('example_bed.bed')
        self.assertEqual(reader, pd.read_table)

        reader = t.get_reader('something.xls')
        self.assertEqual(reader, pd.read_excel)

        reader = t.get_reader('junk.abc')
        self.assertIsNone(reader)

        reader = t.get_reader('junk.odc')
        self.assertIsNone(reader)

    def test_reads_basic_table(self):
        '''
        Is able to parse and report validation on a well-formatted
        general table.
        '''
        t = TableResource()
        is_valid, err = t.validate_type(os.path.join(
            TESTDIR, 'test_general_table.tsv'))
        self.assertTrue(is_valid)
        self.assertIsNone(err)

    def test_reports_unknown_parser(self):
        t = TableResource()
        is_valid, err = t.validate_type(os.path.join(
            TESTDIR, 'something.abc'))
        self.assertFalse(is_valid)
        self.assertEqual(err, PARSER_NOT_FOUND_ERROR) 

    def test_fails_malformatted_basic_table(self):
        t = TableResource()
        is_valid, err = t.validate_type(os.path.join(
            TESTDIR, 'test_malformatted_table.tsv'))
        self.assertFalse(is_valid)
        self.assertEqual(err, PARSE_ERROR)

    def test_handles_comment_headerlines_appropriately(self):
        t = TableResource()
        is_valid, err = t.validate_type(os.path.join(
            TESTDIR, 'test_general_table.with_comment.tsv'))
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
            TESTDIR, 'test_matrix.tsv'))
        self.assertTrue(is_valid)
        self.assertIsNone(err) 

    def test_reads_integer_table(self):
        '''
        Tables of integers also pass validation
        '''
        m = Matrix()
        is_valid, err = m.validate_type(os.path.join(
            TESTDIR, 'test_integer_matrix.tsv'))
        self.assertTrue(is_valid)
        self.assertIsNone(err) 

    def test_reads_table_without_gene_label(self):
        '''
        Tables with a blank first column name are OK
        '''
        m = Matrix()
        is_valid, err = m.validate_type(os.path.join(
            TESTDIR, 'test_integer_matrix.no_gene_label.tsv'))
        self.assertTrue(is_valid)
        self.assertIsNone(err) 

    def test_incorrect_table(self):
        '''
        Tests that a table with a string entry fails
        '''
        m = Matrix()
        is_valid, err = m.validate_type(os.path.join(
            TESTDIR, 'test_incorrect_matrix.tsv'))
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
            TESTDIR, 'test_integer_matrix.no_header.tsv'))
        self.assertFalse(is_valid)
        self.assertEqual(err, NUMBERED_COLUMN_NAMES_ERROR)

    def test_table_without_rownames(self):
        '''
        Tables without row names fails
        '''
        m = Matrix()
        is_valid, err = m.validate_type(os.path.join(
            TESTDIR, 'test_integer_matrix.no_rownames.tsv'))
        self.assertFalse(is_valid)
        self.assertEqual(err, NUMBERED_ROW_NAMES_ERROR)

    def test_duplicate_rownames_fails(self):
        m = Matrix()
        is_valid, err = m.validate_type(os.path.join(
            TESTDIR, 'test_matrix.duplicate_rownames.tsv'))
        self.assertFalse(is_valid)
        self.assertEqual(err, NONUNIQUE_ROW_NAMES_ERROR)

    def test_reads_float_table_with_na(self):
        '''
        Capable of parsing a table containing missing
        data
        '''
        m = Matrix()
        is_valid, err = m.validate_type(os.path.join(
            TESTDIR, 'test_matrix.with_na.tsv'))
        self.assertTrue(is_valid)
        self.assertIsNone(err) 



class TestIntegerMatrix(unittest.TestCase):


    def test_fails_with_float_table(self):
        '''
        Capable of parsing a table of mixed numeric types
        '''
        m = IntegerMatrix()
        is_valid, err = m.validate_type(os.path.join(
            TESTDIR, 'test_matrix.tsv'))
        self.assertFalse(is_valid)

    def test_reads_integer_table(self):
        '''
        Tables of integers pass validation
        '''
        m = IntegerMatrix()
        is_valid, err = m.validate_type(os.path.join(
            TESTDIR, 'test_integer_matrix.tsv'))
        self.assertTrue(is_valid)
        self.assertIsNone(err) 

        m = IntegerMatrix()
        is_valid, err = m.validate_type(os.path.join(
            TESTDIR, 'test_integer_matrix.csv'))
        self.assertTrue(is_valid)
        self.assertIsNone(err) 

    def test_table_without_header(self):
        '''
        Tables without a header row fail
        '''
        m = IntegerMatrix()
        is_valid, err = m.validate_type(os.path.join(
            TESTDIR, 'test_integer_matrix.no_header.tsv'))
        self.assertFalse(is_valid)
        self.assertEqual(err, NUMBERED_COLUMN_NAMES_ERROR)

    def test_reads_table_without_gene_label(self):
        '''
        Tables with a blank first column name are OK
        '''
        m = IntegerMatrix()
        is_valid, err = m.validate_type(os.path.join(
            TESTDIR, 'test_integer_matrix.no_gene_label.tsv'))
        self.assertTrue(is_valid)
        self.assertIsNone(err) 

    def test_table_without_rownames(self):
        '''
        Tables without row names fails
        '''
        m = IntegerMatrix()
        is_valid, err = m.validate_type(os.path.join(
            TESTDIR, 'test_integer_matrix.no_rownames.tsv'))
        self.assertFalse(is_valid)
        self.assertEqual(err, NUMBERED_ROW_NAMES_ERROR)

    def test_duplicate_rownames_fails(self):
        m = IntegerMatrix()
        is_valid, err = m.validate_type(os.path.join(
            TESTDIR, 'test_matrix.duplicate_rownames.tsv'))
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
            TESTDIR, 'test_integer_matrix.with_na.csv'))
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
            TESTDIR, 'test_integer_matrix.with_na_and_float.csv'))
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
            TESTDIR, 'test_integer_matrix.with_multiple_na_and_float.csv'))
        self.assertFalse(is_valid)
        bad_col_str = 'SW5_Treated (column 5)'
        expected_err_str = NON_INTEGER_ERROR.format(cols=bad_col_str)
        self.assertEqual(err, expected_err_str) 

class TestAnnotationMatrix(unittest.TestCase):

    def test_table_without_header(self):
        '''
        Tables without a header row pass, but get warned
        if there are duplicate values
        '''
        t = AnnotationTable()
        is_valid, msg = t.validate_type(os.path.join(
            TESTDIR, 'test_annotation.no_header.tsv'))
        self.assertTrue(is_valid)
        self.assertEqual(msg, MISSING_HEADER_WARNING)

    def test_table_with_single_column_fails(self):
        '''
        Tables with only a single column fails since
        it is not useful
        '''
        t = AnnotationTable()
        is_valid, err = t.validate_type(os.path.join(
            TESTDIR, 'single_column_annotation.tsv'))
        self.assertFalse(is_valid)
        self.assertEqual(err, TRIVIAL_TABLE_ERROR)

    def test_duplicate_rownames_fails(self):
        '''
        Cannot have more than one annotation per 'sample'
        '''
        t = AnnotationTable()
        is_valid, err = t.validate_type(os.path.join(
            TESTDIR, 'two_column_annotation.duplicate_rows.tsv'))
        self.assertFalse(is_valid)
        self.assertEqual(err, NONUNIQUE_ROW_NAMES_ERROR)

    def test_parses_proper_annotations(self):
        t = AnnotationTable()
        is_valid, err = t.validate_type(os.path.join(
            TESTDIR, 'two_column_annotation.tsv'))
        self.assertTrue(is_valid)
        self.assertIsNone(err)

class TestBed(unittest.TestCase):

    def test_bed_without_header_fails(self):
        '''
        Technically, BED format does not allow a header.  
        Since BED files may feed into downstream processes, we 
        reject these malformatted BED files
        '''
        b = BEDFile()
        is_valid, err = b.validate_type(os.path.join(
            TESTDIR, 'bed_with_header.bed'))
        self.assertFalse(is_valid)
        self.assertEqual(err, BED_FORMAT_ERROR.format(cols='2,3'))


    def test_bed_with_extra_fields_passes(self):
        '''
        This allows some of the extended BED formats.
        '''
        b = BEDFile()
        is_valid, err = b.validate_type(os.path.join(
            TESTDIR, 'five_column.bed'))
        self.assertTrue(is_valid)
