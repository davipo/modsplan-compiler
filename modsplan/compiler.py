#!/usr/local/bin/python

# compiler.py
# Modsplan compiler
# Copyright 2013- by David H Post, DaviWorks.com.

import sys
import os.path

from lineparsers import Error as BaseError
from tokenize import Error

import syntax
import defn


default_spec_dir = 'modspecs/'          # default location for language specifications
code_suffix = 'stkvm'                   # name of target language
instr_fmt = '\t%-12s %s'
letters = '_abcdefghijklmnopqrstuvwxyz'
        
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
        self.labelsuffix = {}           # key is label, value is last unique suffix used
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
        self.labelsuffix.clear()
        return self.codegen(self.source_tree)


    def codegen(self, source_node):
        """ Generate code from source_node, using definitions loaded for language.
            Return list of target code instructions (strings)."""
        code = []
        if source_node.comment:
            code.append(';' + source_node.comment)
        # Traverse in preorder, generating code for any defns found
        definition = self.defs.get_defn(source_node)    # find definition matching this node
        if definition:
            code.extend(self.gen_instructions(source_node, definition))
        else:   # no definition found; generate code for any children
            if source_node.isterminal():
                message = 'No definition found for terminal token %s' % source_node
                raise Error(message, self.defs.defn_tree)
            else:
                for child in source_node.children:
                    code.extend(self.codegen(child))
        return code


    def new_label(self, label, source_node, defn_node):
        """ Return a unique label for this node;
            use label + <source line number>, with a letter appended if needed."""
        label += '%d' % source_node.linenum
        suffix = self.labelsuffix.get(label)
        if suffix == None:                  # label not in use: use without a suffix
            suffix = ''
        else:                               # label in use: use next suffix
            index = letters.index(suffix) + 1
            if index >= len(letters):
                raise Error('Too many labels "%s"' % label, defn_node)
            suffix = letters[index]
        self.labelsuffix[label] = suffix
        return label + suffix
    
    
    def get_label(self, label, labels, source_node, defn_node):
        """ Return label with current suffix from labels;
            if not present, get a new one."""
        labelwith = labels.get(label)
        if labelwith == None:
            labelwith = self.new_label(label, source_node, defn_node)
            labels[label] = labelwith
        return labelwith
    
    
    def gen_instructions(self, source_node, instruction_defs, labels=None):
        """ Generate list of target code instructions from source & instruction definitions.
            labels[label] is label with suffix for this definition."""        
        code = []
        if labels == None:
            labels = {}
        for instruction in instruction_defs:
            instr = instruction.firstchild()
            
            if instr.name == 'directive':   # compiler directive, generates one instruction
                directive = instr.findtext()
                arg_defs = instr.findall('carg')
                code.append(self.compiler_directive(source_node, directive, arg_defs, labels))
                
            elif instr.name == 'expansion':     # expand next unused child with this name
                child = source_node.nextchild(defn.childname(instr))
                code.extend(self.codegen(child))
                
            elif instr.name == 'rewrite':       # use instructions from another signature
                signature = self.defs.make_signature(instr.firstchild())
                instructions = self.defs.defns.get(signature)
                if instructions:
                    code.extend(self.gen_instructions(source_node, instructions, labels))
                else:
                    message = 'Rewrite signature "%s" not found' % defn.sig_str(signature)
                    raise Error(message, instruction)
                
            elif instr.name == 'label':     # insert label, compile block below it
                label = self.get_label(instr.findtext(), labels, source_node, instruction)
                code.append(label + ':')
                ### option to indent output instructions under label?
                instructions = instruction.find('instructions?').findall('instruction')
                code.extend(self.gen_instructions(source_node, instructions, labels))

            elif instr.name == 'branch':
                args = []
                for arg in instr.findall('label'):
                    args.append(self.get_label(arg.findtext(), labels, source_node, instr))
                args_str = ', '.join(args)
                opcode = self.defs.first_alternate(instr.name).items[0].text()
                code.append(instr_fmt % (opcode, args_str))
                
            elif instr.name == 'operation':     # generate single instruction
                opcode = instr.findtext()
                args_str = self.gen_args(source_node, instr.findall('oparg'), labels)
                code.append(instr_fmt % (opcode, args_str))
                
            else:
                message = 'Unrecognized instruction kind "%s"' % instr.name
                raise Error(message, self.defs.first_alternate(instr.name))
                ### Error may be in a subsequent alternate, too hard to find which one
            
            if instr.comment and 'm' in self.debug:         # output defn comment
                text = '  ;(' + self.langname + ')' + instr.comment
                if code:
                    code[-1] = code[-1] +  text
                else:
                    code.append(text)
                
        if 'i' in self.debug:
            print '(%s:)' % source_node.name 
            print '\n'.join(code) + '\n'
        return code
        

    def gen_args(self, source_node, arg_defs, labels):
        """ Generate string of code for instruction args from source and arg definitions.
            labels[label] is label with suffix for this definition."""        
        args = []
        for argdef in arg_defs:
            argtype = argdef.firstchild()
            argtext = argtype.findtext()
            
            if argtype.name in ('constant', 'otherarg'):
                args.append(argtext)
            
#             elif argtype.name == 'nonterm':         # for compiler directives
#                 args.append(source_node.firstchild(argtext).findtext())
            
            ### revert to previous, but with '&' prefix for nonterm
            elif argtype.name == 'child':
                child = source_node.nextchild(defn.childname(argtype))
                if child.isterminal():
                    args.append(child.findtext())
                else:
                    for arg in child.children:          # handles quantifiers
                        args.append(arg.findtext())
#                 print 'gen_args', source_node.name, child, args
            
            elif argtype.name == 'terminal':
                child = source_node.nextchild(argtext)  # argtext is tokenkind in source,
                args.append(child.text)                 #   substitute token text
                
            elif argtype.name == 'directive':
                arg_defs = argtype.findall('carg')
                args.append(self.compiler_directive(source_node, argtext, arg_defs, labels))
                
            else:
                message = 'Unrecognized argument kind "%s"' % argtype.name
                raise Error(message, self.defs.first_alternate(argtype.name))
                ### Error may be in a subsequent alternate, too hard to find which one
        return ', '.join(args)
        

    def compiler_directive(self, source_node, directive, arg_defs, labels):
        """ Generate code per compiler directive, using source and arg definitions.
            labels[label] is label with suffix for this definition."""        
        args_str = self.gen_args(source_node, arg_defs, labels)
        if directive == 'getsymbol':
            pass
        return instr_fmt % ('.' + directive, args_str)


def compile_src(sourcepath, codepath='', spec_dir=None, debug=''):
    """ Compile source code from sourcepath, write target code to codepath (if given),
        return lines of target code in a single string.
        If codepath is '*', write to sourcepath.<code_suffix>.
        Optional specification directory and debug flags."""
    langname = sourcepath.rpartition('.')[-1]
    try:
        compiler = Compiler(langname, spec_dir, debug)      # initialize for langname
        code = compiler.compile(sourcepath)                 # compile source
        codestring = '\n'.join(code) + '\n'
        if codepath:
            if codepath == '*':
                codepath = sourcepath + '.' + code_suffix
            with open(codepath, 'w') as outfile:
                outfile.write(codestring)
        return codestring
    except (None if debug else BaseError) as exc:
        print exc


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
        codestring = compile_src(sourcepath, '*', spec_dir, debug)
        print
        print codestring
    else:
        print 'Usage: python compiler.py <source_path> [<specification_dir>] [-<debug_flags>]'
