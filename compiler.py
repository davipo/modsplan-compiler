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
instr_fmt = '\t%-12s %s'
        
class Compiler:
    """ Universal compiler: reads language specs, compiles specified language."""
    
    def __init__(self, langname, spec_dir=None, debug=''):
        """ Load language specs for langname.
            Optional specification directory, debugging flags."""
        self.langname = langname
        self.debug = debug          # debugging flags
        self.source_tree = None     # last tree parsed from source
        if spec_dir == None:
            spec_dir = default_spec_dir
        langpath = os.path.join(spec_dir, langname)
        self.parser = syntax.SyntaxParser(langpath, debug)  # load langname.{tokens, syntax}
        self.defs = defn.Definitions()          # initialize defn parser
        self.defs.load(langpath)                # load semantics from langname.defn
        if 'e' in debug:
            print self.defs.defn_tree.show()        # parse tree of language definitions
        if 'g' in debug:
            print self.defs.show()                  # definition signatures
        if 'd' in debug:
            print self.defs.show(sigs_only=False)   # definition sigs with instructions


    def compile(self, source_filepath):
        """ Compile source code for initialized language, 
            return list of target code instructions (strings)."""
        print '\nParsing %s ...' % source_filepath
        self.source_tree = self.parser.parse(source_filepath)
        return self.codegen(self.source_tree)
#         return ['\t' * (':' not in line) + line for line in code]


    def codegen(self, source_node):
        """ Generate code from source_node, using definitions loaded for language.
            Return list of target code instructions (strings)."""
        code = []
        # Traverse in preorder, generating code for any defns found
        definition = self.defs.get_defn(source_node)    # find definition matching this node
        if definition:
            code.extend(self.gen_instructions(source_node, definition))
        else:   # no definition found; generate code for any children
            if source_node.isterminal():
                if source_node.name == 'COMMENT':
                    code.append(instr_fmt % ('', ';' + source_node.text))
                else:
                    message = 'No definition found for terminal token %s' % source_node.name
                    raise self.defs.err.msg(message)
            else:
                for child in source_node.children:
                    code.extend(self.codegen(child))
        return code


    def gen_instructions(self, source_node, instruction_defs):
        """ Generate list of target code instructions from source & instruction definitions."""        
        code = []
        for instruction in instruction_defs:
            instr = instruction.firstchild()
            
            if instr.name == 'directive':   # compiler directive, generates single instruction
                directive = instr.findtext()
                arg_defs = instr.findall('carg')
                code.append(self.compiler_directive(source_node, directive, arg_defs))
                
            elif instr.name == 'expansion':     # expand next unused child with this name
                child = source_node.nextchild(defn.childname(instr))
                code.extend(self.codegen(child))
                
            elif instr.name == 'rewrite':       # use instructions from another signature
                signature = self.defs.make_signature(instr.firstchild())
                instructions = self.defs.defns.get(signature)
                if instructions:
                    code.extend(self.gen_instructions(source_node, instructions))
                else:
                    message = 'Rewrite signature "%s" not found' % defn.sig_str(signature)
                    raise self.defs.err.msg(message)
                
            elif instr.name == 'label':     # insert label, compile block below it
                label = instr.findtext()
                code.append(label + ':')
                ### option to indent output instructions under label?
                instructions = instruction.find('instructions?').findall('instruction')
                code.extend(self.gen_instructions(source_node, instructions))
                
            elif instr.name == 'operation':     # generate single instruction
                opcode = instr.findtext()
                args_str = self.gen_args(source_node, instr.findall('oparg'))
                code.append(instr_fmt % (opcode, args_str))
                
            elif instr.name == 'endline':
                comment = instr.find('COMMENT')     # defn comment, not normally output
                if comment and 'c' in debug:
                    text = ';(' + self.langname + ')' + comment.findtext()
                    code.append(instr_fmt % ('', text))
            else:
                message = 'Unrecognized instruction "%s"' % instr.name
                raise self.defs.err.msg(message)
                
        if 'i' in self.debug:
            print '(%s:)' % source_node.name 
            print '\n'.join(code) + '\n'
        return code
        

    def gen_args(self, source_node, arg_defs):
        """ Generate string of code for instruction args from source and arg definitions."""
        args = []
        for argdef in arg_defs:
            argtype = argdef.firstchild()
            argtext = argtype.findtext()
            
            if argtype.name in ('constant', 'label'):
                args.append(argtext)
                
            elif argtype.name == 'nonterm':         # for compiler directives
                args.append(source_node.firstchild(argtext).findtext())
            
            elif argtype.name == 'terminal':
                child = source_node.nextchild(argtext)      # argtext is tokenkind in source,
                args.append(child.text)                     #   substitute token text
                
            elif argtype.name == 'directive':
                arg_defs = instr.findall('carg')
                args.append(self.compiler_directive(source_node, argtext, arg_defs))
                
            else:
                message = 'Unrecognized argument "%s"' % argtype.name
                raise self.defs.err.msg(message)
        return ', '.join(args)
        

    def compiler_directive(self, source_node, directive, arg_defs):
        """ Generate code per compiler directive, using source and arg definitions."""
        args_str = self.gen_args(source_node, arg_defs)
        if directive == 'getsymbol':
            pass
        return instr_fmt % ('.' + directive, args_str)


if __name__ == '__main__':
    debug = ''                      # default debugging output
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
            print '\n'.join(code) + '\n'
        except (None if debug else Error) as exc:
            print exc
    else:
        print 'Usage: ./compiler.py <source_filename> [<specification_directory>] [-<debug_flags>]'

