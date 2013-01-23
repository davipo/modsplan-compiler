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
    
    def __init__(self, langname, spec_dir=None, debug=''):
        """ Load language specs for langname.
            Optional specification directory, debugging flags."""
        self.langname = langname
        self.debug = debug          # debugging flags
        self.source_tree = None     # last tree parsed from source
        self.source_err = None      # set in compile(), for reporting errors in source
        if spec_dir == None:
            spec_dir = default_spec_dir
        langpath = os.path.join(spec_dir, langname)
        self.parser = syntax.SyntaxParser(langpath, debug)  # load langname.{tokens, syntax}
        self.defs = defn.Definitions()                # initialize defn parser
        self.defs.load(langpath)                      # load semantics from langname.defn


    def compile(self, source_filepath):
        """ Compile source code for initialized language, 
            return list of target code instructions (strings)."""
        code = []
        print '\nParsing %s ...' % source_filepath
        self.source_tree = self.parser.parse(source_filepath)
        if 't' in self.debug:
            print '\n\nTree:\n'
            print self.source_tree.show()
        self.source_err = Error(source_filepath)
        code = self.codegen(self.source_tree)
        return code


    def codegen(self, source_node):
        """ Generate code from source_node, using definitions loaded for language.
            Return list of target code instructions (strings)."""
        code = []
        # Traverse in preorder, generating code for any defns found
        defn = self.defs.find(source_node)      # find a definition matching this node
        if defn:
            code.extend(gen_instructions(source_node, defn.instructions))
        else:   # no definition found; generate code for any children
            if not source_node.isterminal():
                for child in source_node.children:
                    code.extend(self.codegen(child))
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
    debug = 't'              # default debugging output
    if 2 <= len(sys.argv) <= 4:
        sourcepath = sys.argv[1]
        spec_dir = None                 # specifications directory, use default if None
        for arg in sys.argv[2:]:
            if arg.startswith('-'):
                debug = arg[1:]
            else:
                spec_dir = arg
        langname = sourcepath.rpartition('.')[-1]
        try:
            compiler = Compiler(langname, spec_dir, debug)      # initialize for langname
            code = compiler.compile(sourcepath)                 # compile source
            print code
        except Error as exc:
            print exc
    else:
        print 'Usage: ./compiler.py <source_filename> [<specification_directory>] [-<debug_flags>]'

