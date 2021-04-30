import uuid
import os
import json
import unittest.mock as mock

from django.core.exceptions import ImproperlyConfigured

from django.conf import settings

from api.tests.base import BaseAPITestCase
from api.tests import test_settings


class FilterTests(BaseAPITestCase):
    '''
    This class tests the binary filter operations in api/filters.py

    These filters are used for filtering resource content (e.g. for a filtered
    subset of a table).

    For table-based resources, we rely on Pandas types and filtering operations.
    However, we also allow limited filtering of JSON resources and these filters
    are often used for that.
    '''

    def test_numerical_operators(self):
        '''
        Test the purely numerical operators.
        These are the ones that only make sense 
        in the context of numbers and should return 
        False if given non-numerics.

        We don't raise exceptions when non-numerics are
        encountered since different analysis tools
        can mark NaN in a variety of ways.
        '''
        lt = settings.OPERATOR_MAPPING[settings.LESS_THAN]
        self.assertTrue(lt(2,3))
        self.assertFalse(lt(34,2))
        self.assertFalse(lt('a',2))
        self.assertFalse(lt(None,2))
        self.assertFalse(lt('a',None))

        gt = settings.OPERATOR_MAPPING[settings.GREATER_THAN]
        self.assertTrue(gt(3,2))
        self.assertFalse(gt(1,2))
        self.assertFalse(gt('a',2))
        self.assertFalse(gt(None,2))
        self.assertFalse(gt('a',None))

        lte = settings.OPERATOR_MAPPING[settings.LESS_THAN_OR_EQUAL]
        self.assertTrue(lte(2,3))
        self.assertTrue(lte(3,3))
        self.assertFalse(lte(34,2))
        self.assertFalse(lte('a',2))
        self.assertFalse(lte(None,2))
        self.assertFalse(lte('a',None))

        gte = settings.OPERATOR_MAPPING[settings.GREATER_THAN_OR_EQUAL]
        self.assertTrue(gte(3,2))
        self.assertTrue(gte(3,3))
        self.assertFalse(gte(1,2))
        self.assertFalse(gte('a',2))
        self.assertFalse(gte(None,2))
        self.assertFalse(gte('a',None))

        abslt = settings.OPERATOR_MAPPING[settings.ABS_VAL_LESS_THAN]
        self.assertTrue(abslt(-2,3))
        self.assertFalse(abslt(-34,2))
        self.assertTrue(abslt(1,2))
        self.assertFalse(abslt('a',2))
        self.assertFalse(abslt(None,2))
        self.assertFalse(abslt('a',None))

        absgt = settings.OPERATOR_MAPPING[settings.ABS_VAL_GREATER_THAN]
        self.assertTrue(absgt(-3,2))
        self.assertFalse(absgt(-1,2))
        self.assertTrue(absgt(4,2))
        self.assertFalse(absgt('a',2))
        self.assertFalse(absgt(None,2))
        self.assertFalse(absgt('a',None))

        # the requests can specify [eq], =, or ==
        # Test those all at once
        ops = [
            settings.OPERATOR_MAPPING[settings.EQUAL_TO],
            settings.OPERATOR_MAPPING['='],
            settings.OPERATOR_MAPPING['==']
        ]
        for eq in ops:
            self.assertTrue(eq('a','a'))
            self.assertTrue(eq(2,2))
            self.assertTrue(eq(-3.2, -3.2))
            self.assertFalse(eq('a',2))
            self.assertFalse(eq(2,'a'))
            self.assertFalse(eq('a','b'))
            self.assertFalse(eq('a','A'))
            self.assertFalse(eq(3,2))

    def test_string_capable_operators(self):
        '''
        This tests that we have the expected behavior
        from the comparisons that can be performed on strings
        such as equals, startswith, etc.
        '''
        op = settings.OPERATOR_MAPPING[settings.CASE_INSENSITIVE_EQUALS]
        self.assertTrue(op('xY', 'xy'))
        self.assertTrue(op('xy', 'xy'))
        self.assertFalse(op('x', 'y'))
        self.assertTrue(op('2', '2'))
        self.assertFalse(op('3', '2'))

        op = settings.OPERATOR_MAPPING[settings.STARTSWITH]
        self.assertTrue(op('abcd', 'abc'))
        self.assertTrue(op('ABCD', 'abc'))
        self.assertFalse(op('ABC', 'y'))
        self.assertTrue(op('23', '2'))
        self.assertFalse(op('33', '22'))

    def test_isin_op(self):
        '''
        Tests the "is in" operator, which checks if a 
        string is contained in a list of strings.

        Used, for instance, to filter a table to only
        those genes that are in a particular gene set
        '''
        op = settings.OPERATOR_MAPPING[settings.IS_IN]
        self.assertTrue(op('abc','xyz,abc,qbc'))
        self.assertTrue(op('1','1,2,3'))
        self.assertTrue(op('abc','xyz,  abc,      qbc')) # space is fine
        self.assertFalse(op('Abc','xyz,abc,qbc')) # sensitive to case
        self.assertFalse(op('Abc','xyz'))
