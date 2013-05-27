#!/usr/local/bin/python

# compiler.py
# Modsplan compiler
# Copyright 2013- by David H Post, DaviWorks.com.

import sys
import os.path

from lineparsers import Error

import syntax
import defn


default_spec_dir = 'modspecs/'              # default directory for language specifications
default_defn_grammar_dir='defn_grammar/'    # default directory for defn grammar
code_suffix = 'sbil'                        # name of target language
indentation = '    '                        # one indent, for target code
letters = '_abcdefghijklmnopqrstuvwxyz'     # used as suffix to make labels unique


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
        self.comments = []          # collected comments, to insert after current instruction
        self.level = 0              # phrase level; 0 when generating whole instructions
        
        self.parser = syntax.SyntaxParser(langpath, debug)  # load langname.{tokens, syntax}
        self.defs = defn.Definitions(default_defn_grammar_dir)    # initialize defn parser
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
            return lines of target code, indented appropriately."""
        if '2' in self.debug:
            print '\nParsing %s ...' % source_filepath
        self.source_tree = self.parser.parse(source_filepath)
        
        self.labelsuffix.clear()
        self.comments = []
        self.level = 0
        codelines = []
        
        # Output initial comments
        for child in self.source_tree.children:
            if child.name == 'COMMENT':
                codelines += [';' + child.findtext()]
        
        # Generate code
        codelines += self.codegen(self.source_tree)
        
        # Indent lines of target code appropriately
        indent = 0
        lines = []
        for line in codelines:
            if line.endswith(':'):              # label, no indent
                lines.append(line)
            else:
                if line == '.indent':
                    indent += 1
                elif line == '.dedent':
                    indent -= 1
                else:
                    lines.append(indent * indentation + line)
        return lines


    def codegen(self, source_node):
        """ Generate code from source_node, using definitions loaded for language.
            Return list of target code instructions (strings)."""
        code = []
        
        # Traverse in preorder, generating code for any defns found
        definition = self.defs.get_defn(source_node)    # find definition matching this node
        if definition:
            code += self.gen_instructions(source_node, definition)
            #print 'code for ' + source_node.name
            #print '   ', code
            #print
        
        else:   # no definition found; generate code for any children
            if source_node.isterminal():
                if source_node.name != 'COMMENT':
                    code += [source_node.findtext()]    # insert text of terminal nodes
            else:
                for child in source_node.children:
                    code += self.codegen(child)
        
        return code
    

    def new_label(self, label, source_node, defn_node):
        """ Return a unique label for this node;
            use label + <source line number>, with a letter appended if needed."""
        label += '%d' % source_node.location.linenum
        suffix = self.labelsuffix.get(label)
        if suffix == None:                  # label not in use: use without a suffix
            suffix = ''
        else:                               # label in use: use next suffix
            index = letters.index(suffix) + 1
            if index >= len(letters):
                raise defn_node.location.error('Too many labels "%s"' % label)
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
            if not instruction.children:
                continue
            instr = instruction.firstchild()
            
            if instr.name == 'expansion':       # expand next unused child with this name
                child = source_node.nextchild(defn.childname(instr), loc=instr)
                code += self.codegen(child)
                
            elif instr.name == 'rewrite':       # use instructions from another signature
                signature = self.defs.make_signature(instr.firstchild())
                instructions = self.defs.defns.get(signature)
                if instructions:
                    code += self.gen_instructions(source_node, instructions, labels)
                else:
                    message = 'Rewrite signature "%s" not found' % defn.sig_str(signature)
                    raise instruction.location.error(message)
                
            elif instr.name == 'label':     # insert label, compile block below it
                label = self.get_label(instr.findtext(), labels, source_node, instruction)
                code.append(label + ':')
                instructions = instruction.find('instructions?').findall('instruction')
                code += self.gen_instructions(source_node, instructions, labels)
                
            elif instr.name == 'branch':
                args = []
                for arg in instr.findall('label'):
                    args.append(self.get_label(arg.findtext(), labels, source_node, instr))
                opcode = defn.remove_quotes(instr.findtext())
                code.append(opcode + ' ' + ', '.join(args))
                
            elif instr.name == 'word+':         # generate a phrase or line of code
                self.level += 1
                words = [self.gen_word(source_node, word) for word in instr.findall('word')]
                self.level -= 1
                words = filter(str.strip, words)    # remove empty words
                phrase = ' '.join(words)
                phrase = phrase.replace(' (', '(').replace('( ', '(').replace(' )', ')')
                    # fix paren spacing
                code.append(phrase)
                
            else:
                location = self.defs.first_alternate(instr.name).location
                raise location.error('Unrecognized instruction kind "%s"' % instr.name)
                ### Error may be in a subsequent alternate, too hard to find which one
        
        # Collect comments
        if not source_node.isterminal():
            for child in source_node.children:
                if child.name == 'COMMENT':
                    self.comments += [';' + child.findtext()]
        
        if self.level == 0:             # if generating whole instructions,
            code += self.comments       #   output collected comments
            self.comments = []
        
        if 'i' in self.debug:
            print '(%s:)' % source_node.name
            print '\n'.join(code) + '\n'
        return code
    
    
    def gen_word(self, source_node, word_def, use=True):
        """ Generate code string from source and word definition.
            If 'use' false, ignore use status of parse nodes."""        
        wordtype = word_def.firstchild()
        
        if wordtype.name in ('LITERAL'):
            return defn.remove_quotes(wordtype.findtext())
                
        elif wordtype.name == 'child':
            child = source_node.nextchild(defn.childname(wordtype), use, loc=wordtype)
            return ' '.join(self.codegen(child))
            
        elif wordtype.name == 'directive':
            return self.compiler_directive(source_node, wordtype)
            
        else:
            location = self.defs.first_alternate(wordtype.name).location
            raise location.error('Unrecognized word kind "%s"' % wordtype.name)
            ### Error may be in a subsequent alternate, too hard to find which one
    

    def compiler_directive(self, source_node, directive):
        """ Generate code per compiler directive, using source and arg definitions.
            Ignore use status of parse nodes when generating args."""
        name = directive.findtext()
        arg_defs = directive.findall('word')
        
        if name == 'count':         # number of children of its argument
            firstarg = arg_defs[0]
            nodename = defn.childname(firstarg)
            codestring = str(source_node.firstchild(nodename, loc=firstarg).numchildren())
            
        elif name == 'again':       # reuse child
            codestring = self.gen_word(source_node, arg_defs[0], use=False)
            
        elif name == 'commasep':    # separate children of first arg with commas
            firstarg = arg_defs[0]
            nodename = defn.childname(firstarg)
            childnodes = source_node.firstchild(nodename, loc=firstarg).children
            childtexts = [' '.join(self.codegen(child)) for child in childnodes]
            codestring = ', '.join(childtexts)
        
        else:
            args = [self.gen_word(source_node, argdef, use=False) for argdef in arg_defs]
            codestring = '.' + name
            if args:
                codestring += ' ' + ', '.join(args)
            
        return codestring
        

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
    
    except (None if 'b' in debug else Error) as exc:
        print exc
        return None


if __name__ == '__main__':
    debug = '1'                     # default debugging output
    if 2 <= len(sys.argv) <= 4:
        sourcepath = sys.argv[1]
        spec_dir = None                 # specifications directory, use default if None
        for arg in sys.argv[2:]:
            if arg.startswith('-'):
                debug = arg[1:]
            else:
                spec_dir = arg
        codepath = '*' if 'w' in debug else ''
        codestring = compile_src(sourcepath, codepath, spec_dir, debug)
        print
        print codestring
    else:
        print 'Usage: python compiler.py <source_path> [<specification_dir>] [-<debug_flags>]'
