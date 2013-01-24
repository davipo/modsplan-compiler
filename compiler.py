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
        self.defs = defn.Definitions()          # initialize defn parser
        self.defs.load(langpath)                # load semantics from langname.defn
        self.defn_err = Error(langpath)         # for reporting errors in langname.defn
        if 'e' in debug:
            print self.defs.defn_tree.show()        # parse tree of language definitions
        if 'g' in debug:
            print self.defs.show(sigs_only=True)    # definition signatures
        if 'd' in debug:
            print self.defs.show()                  # definition sigs with instructions


    def compile(self, source_filepath):
        """ Compile source code for initialized language, 
            return list of target code instructions (strings)."""
        print '\nParsing %s ...' % source_filepath
        self.source_tree = self.parser.parse(source_filepath)
        if 't' in self.debug:
            print '\n\nTree:\n'
            print self.source_tree.show()
        self.source_err = Error(source_filepath)
        return self.codegen(self.source_tree)


    def codegen(self, source_node):
        """ Generate code from source_node, using definitions loaded for language.
            Return list of target code instructions (strings)."""
        code = []
        # Traverse in preorder, generating code for any defns found
        defn = self.defs.find(source_node)      # find a definition matching this node
        if defn:
            code.extend(self.gen_instructions(source_node, defn))
        else:   # no definition found; generate code for any children
            if source_node.isterminal():
                message = 'Reached terminal source node %s prematurely' % source_node.name
                raise Error().msg(message)
            else:
                for child in source_node.children:
                    code.extend(self.codegen(child))
        return code


    def gen_instructions(self, source_node, instr_defn):
        """ Generate list of target instruction codes from source node & instr_defn."""        
        code = []
        for instruction in instr_defn:
            instr = instruction.first()
            if instr.name == 'directive':
                self.compiler_directive(source_node, instr)     ### discard return value?
            elif instr.name == 'expansion':
                child_name = instr.findtext()
                child = source_node.next(child_name)
                code.extend(self.codegen(child))
            elif instr.name == 'rewrite':
                pass    ### implement later
            elif instr.name == 'label':
                code.append(instr.findtext() + ':')
                ### display output instructions indented?
                instructions_defn = instruction.first('instructions').children
                code.extend(self.gen_instructions(source_node, instructions_defn))
            elif instr.name == 'operation':
                code.append(self.gen_operation(source_node, instr))     # single instruction
            elif instr.name == 'endline':
                pass
            else:
                message = 'Unrecognized instruction %s' % instr.name
                raise self.defn_err.msg(message)
        return code
            
      
    def gen_operation(self, source_node, operation):
        """ Generate code (string) for operation instruction from source & operation defn."""
        ### handle compiler directive also here?
        ### factor out gen_args()
        args = []
        for oparg in operation.findall('oparg'):
            argtype = oparg.first()
            if argtype.name in ('constant', 'label'):
                args.append(argtype.findtext())
            elif argtype.name == 'terminal':
                child_name = argtype.findtext()
                child = source_node.next(child_name)
                args.append(child.text)
            elif argtype.name == 'directive':
                args.append(self.compiler_directive(source_node, argtype))
        opcode = operation.findtext()
        return opcode + ' \t' + ', '.join(args)


    def compiler_directive(self, source_node, instr):
        """ Process compiler directive, using source data; return string for oparg."""
        return ''


    def gen_args(self, source_node, args):
        """ Generate code for instruction args from source and args defn."""
        return ''
        

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

