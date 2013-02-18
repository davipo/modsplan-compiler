#!/usr/local/bin/python

# test.py
# Modsplan tests
# Copyright 2013- by David H Post, DaviWorks.com.

import unittest
import os

import modsplan.compiler
import modsplan.lineparsers

source_dir = 'sample_source'


class TestCompiler(unittest.TestCase):
    """ Run some tests on compiler."""
    
    
    def setUp(self):
        """ """
        pass


    def test_compile(self):
        self.check_src('bazgoop.L0')
        self.check_src('simplepy.L0')
    
    
    def check_src(self, sourcename):
        """ Compile sourcename from source_dir, check code against previous."""
        sourcepath = os.path.join(source_dir, sourcename)
        self.check_with_prev(sourcepath)
        
    
    def check_with_prev(self, sourcepath):
        """ Compile source at sourcepath, compare code to previously compiled code."""
        code = modsplan.compiler.compile_src(sourcepath)
        with open(sourcepath + '.stkvm') as codefile:
            prevcode = codefile.read()
        self.assertEqual(code, prevcode)
     
     
    def test_import(self):
        """ Parse lines of import_test.L0, check that imports are processed correctly."""
        filename = 'import_test.L0'
        sourcepath = os.path.join(source_dir, filename)
        lines = modsplan.lineparsers.LineInfoParser(sourcepath, True).readlines()
        text = ''.join(lines)
        with open(sourcepath + '.txt') as f:
            prevtext = f.read()
        self.assertEqual(text, prevtext)
     
     
    def test_tokenizer(self):
        """ Tokenize a test file, check tokens."""
        filename = 'simplepy.L0'
        

if __name__ == '__main__':
    unittest.main()
    
