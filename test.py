#!/usr/local/bin/python

# test.py
# Modsplan tests
# Copyright 2013- by David H Post, DaviWorks.com.

import unittest
import os

import compiler


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
        code = compiler.compile_src(sourcepath)
        with open(sourcepath + '.code') as codefile:
            prevcode = codefile.read()
        self.assertEqual(code, prevcode)
        

if __name__ == '__main__':
    unittest.main()
    
