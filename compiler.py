#!/usr/local/bin/python

# compiler.py
# Modsplan compiler
# Copyright 2013- by David H Post, DaviWorks.com.

import sys
import os.path

from grammar import Error
import syntax
import defn

        
class Compiler:
    """ Universal compiler: reads language specs, compiles specified language."""
    
    def __init__(self, langname, grammar_dir='grammars/'):
        """ Load language specs for langname."""
        langpath = os.path.join(grammar_dir, langname)
        try:
            self.parser = syntax.SyntaxParser(langpath)   # load langname.{tokens, syntax}
            if 's' in debug:
                self.parser.syntax.show()
            if 'p' in debug:
                print self.parser.syntax.show_prefixes()
            self.defs = defn.Definitions()                # initialize defn parser
            self.defs.load(langpath)                      # load semantics from langname.defn
        except Error as exc:
            print exc


    def compile(self, source_filepath):
        """ Compile source code for selected language, return instruction code."""
        code = None
        try:
            print '\n Parsing %s ... \n' % source_filepath
            source_tree = self.parser.parse(source_filepath)
            if 't' in debug:
                print '\n\nTree:\n'
                print source_tree.show()
            code = self.codegen(source_tree)
        except Error as exc:
            print exc
        return code


    def codegen(self, source_tree):
        """ Generate code from source_tree, using definitions loaded for language.
            Return list of instructions (strings)."""
        code = []
        # Process source tree, looking up definitions, emitting code
        
        
        return code
            
            

if __name__ == '__main__':
    debug = '.'              # default debugging output
#     debug = 'or345t'
    
    if len(sys.argv) in (2, 3):
        if len(sys.argv) == 3:
            debug = sys.argv[2]
        source_filepath = sys.argv[1]
        discard, sep, langname = source_filepath.rpartition('.')
        compiler = Compiler(langname)                   # initialize compiler for langname
        code = compiler.compile(source_filepath)        # compile source
        print code
    else:
        print 'Usage: ./compiler.py <source_filename> [<debug_flags>]'

