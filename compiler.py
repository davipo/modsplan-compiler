#!/usr/local/bin/python

# compiler.py
# Modsplan compiler
# Copyright 2013- by David H Post, DaviWorks.com.

import sys
import os.path

from grammar import Error
import syntax
import defn

        
default_spec_dir = 'modspecs/'          # default location for language specifications

        
class Compiler:
    """ Universal compiler: reads language specs, compiles specified language."""
    
    def __init__(self, langname, spec_dir=None):
        """ Load language specs for langname."""
        self.langname = langname
        self.source_path = ''       # filepath of last source compiled
        self.source_tree = None     # last tree parsed from source
        self.source_err = None      # set in compile(), for reporting errors in source
        if spec_dir == None:
            spec_dir = default_spec_dir
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
            self.source_err = Error(source_filepath)
            code = self.codegen(source_tree)
        except Error as exc:
            print exc
        return code


    def codegen(self, source_tree):
        """ Generate code from source_tree, using definitions loaded for language.
            Return list of target code instructions (strings)."""
        code = []
        # Process source tree, looking up definitions, emitting code
        # Follow first child until we find an item for which we have some definitions
        item = source_tree
        while item.name not in self.defs.defns:
            item = item.first()         # will raise error if no children
            
        definitions = self.defs.defns[item.name]
        for defn in definitions:
            # Does defn match item?
            if item.isterminal():
                match = (defn.text == item.text)
            else:  # item is nonterminal
                # Does defn match item args?
                match = (defn.args == [child.name for child in item.children])
            if match:
                # we have a match, generate instructions
                code.extend(gen_instructions(item, defn.instructions))
                break
        return code
            
            
            
    def gen_instructions(self, item, instructions):
        """ Given instructions tree for item, generate list of target instruction code."""        
        for instruction in defn.instructions:
            instr = instruction.first()
            if instr.name == 'directive':
                direc = instr.first()
                if direc.name == 'identifier':          # compiler directive
                    pass
                elif direc.name == 'child':             # expansion
                    code.extend(self.codegen(direc))
                elif direc.name == 'signature':         # rewrite
                    pass
            elif instr.name == 'label':
                code.append(instr.label + ':')
                code.extend(self.gen_instructions(item, instr.instructions))
            elif instr.name == 'operation':
                code.append(self.gen_operation(instr))
            elif instr.name == 'endline':
                pass        # end of instructions for this defn
            else:
                message = 'Unrecognized instruction %s' % instr.name
                ### which file is this an error in?  :-)
                raise Error().msg(message)
        return code
            
      
    def gen_operation(self, operation):
        """ Generate code for an operation instruction."""
        
        argstring = ''
        opcode = operation.findtext()
        return opcode + ' \t' + argstring
        
        

if __name__ == '__main__':
    debug = '.'              # default debugging output
#     debug = 'or345t'
    
    if 2 <= len(sys.argv) <= 4:
        sourcepath = sys.argv[1]
        spec_dir = None                 # specifications directory, use default if None
        for arg in sys.argv[2:]:
            if arg.startswith('-'):
                debug = arg[1:]
            else:
                spec_dir = arg
    
        discard, sep, langname = sourcepath.rpartition('.')
        compiler = Compiler(langname, spec_dir)     # initialize compiler for langname
        code = compiler.compile(sourcepath)         # compile source
        print code
    else:
        print 'Usage: ./compiler.py <source_filename> [<specification_directory>] [-<debug_flags>]'

