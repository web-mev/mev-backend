import unittest

from api.public_data.gdc.gdc import GDCDataSource
from api.public_data.gdc.tcga import TCGADataSource, TCGARnaSeqDataSource


class TestGDC(unittest.TestCase): 
    def test_dummy(self):
        self.assertTrue(True)


class TestTCGA(unittest.TestCase): 
    def test_dummy(self):
        self.assertTrue(True)


class TestTCGARnaSeq(unittest.TestCase): 
    def test_dummy(self):
        ds = TCGARnaSeqDataSource()
        self.assertTrue(True)
