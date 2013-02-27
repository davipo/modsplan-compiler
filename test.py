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
        self.check_import('import_test.L0')
        self.check_src('import_test.L0')
    
    
    def check_src(self, sourcename):
        """ Compile sourcename from source_dir, check code against previous."""
        sourcepath = os.path.join(source_dir, sourcename)
        self.check_with_prev(sourcepath)
        
    
    def check_with_prev(self, sourcepath):
        """ Compile source at sourcepath, compare code to previously compiled code."""
        code = modsplan.compiler.compile_src(sourcepath)
        if code:
            with open(sourcepath + '.' + modsplan.compiler.code_suffix) as codefile:
                prevcode = codefile.read()
            self.assertEqual(code, prevcode)
     
     
    def check_import(self, filename):
        """ Parse lines of filename, check that imports are processed correctly."""
        sourcepath = os.path.join(source_dir, filename)
        lines = modsplan.lineparsers.LineInfoParser(sourcepath, True).readlines()
        if lines:
            text = ''.join(lines)
            with open(sourcepath + '.txt') as f:
                prevtext = f.read()
            self.assertEqual(text, prevtext)
     

if __name__ == '__main__':
    unittest.main()
    
