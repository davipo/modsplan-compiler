# defn.py
# Modsplan .defn parser
# Copyright 2011-2013 by David H Post, DaviWorks.com.

import os.path

import syntax
from grammar import Error


class DefnNode:  #### not used ####
    
    def __init__(self, instructions):
        self.instructions = instructions    # list of code generation instructions
        ### any other data? If not, we don't need this class.

    def __str__(self):
        return self.instructions.show()
    

class Definitions:
    """ Holds semantic definitions (used to generate code from syntax trees)."""
    
    def __init__(self, defn_grammar_dir='defn_grammar/'):
        """ Initialize defn parser to prepare for parsing .defn specs."""
        defn_path = os.path.join(defn_grammar_dir, 'defn')
        self.defn_tree = None   # parse tree of last definitions loaded; set by load()
        self.defn_parser = syntax.SyntaxParser(defn_path)   # use defn.tokens, defn.syntax
        self.defns = dict()     # Dictionary of definitions: 
                                #   key is signature (list of strings for name and args), 
                                #   value is a list of instructions for this defn.
        
        
    def load(self, langpath):
        """ Load definitions from langpath.defn file."""
        # Use a SyntaxParser to load definitions into a parse tree.
        self.defn_tree = self.defn_parser.parse(langpath + '.defn')

        # Extract definitions from tree
        self.defns.clear()
        for definition in self.defn_tree.findall('definition'):
            signature = [node.findtext() for node in definition.firstchild().children]
            ### need to get subtypes
            instructions = definition.firstchild('instructions')
            ### decode instructions here?
            self.defns[tuple(signature)] = instructions.children
   
   
    def get_defn(self, source_node):
        """ Return a list of instructions for the defn matching source_node, or None."""
        signature = [source_node.name]
        if source_node.isterminal():
            signature.append(repr(source_node.text))    ### add quotes -- not reliable!!
        else:           
            signature += [child.name for child in source_node.children]
        return self.defns.get(tuple(signature))
    
    
    def show(self, sigs_only=True):
        """ Return string display of sorted definitions."""
        display = '\n'
        sigs = self.defns.keys()
        sigs.sort()
        for sig in sigs:
            display += sig[0] + '(' + ' '.join(sig[1:]) + ')\n'
            if not sigs_only:
                display += '\n'.join([ instr.show() for instr in self.defns[sig] ]) + '\n'
        return display + '\n'
    

if __name__ == '__main__':
    defs = Definitions()
    lang = 'modspecs/L0'
    defs.load(lang)
    print defs.show()


