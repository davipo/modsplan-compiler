# defn.py
# Modsplan .defn parser
# Copyright 2011-2013 by David H Post, DaviWorks.com.

import os.path

import syntax
from grammar import Error


class DefnNode:
    
    def __init__(self, content, instructions):
#         self.name = name                    # name of node (nonterminal or terminal)
        self.text = None                    # text if terminal node
        self.args = None                    # list of arguments if nonterminal
        self.instructions = instructions    # list of code generation instructions
        if isinstance(content, str):
            self.text = content
        elif isinstance(content, list):
            self.args = content
        else:
            raise Error().msg('Invalid content for DefnNode %s' % name)


    def __str__(self):
        s = '<'
        if self.text == None:
            s += str(self.args)
        else:
            s += self.text
        return s + '>'
    

class Definitions:
    """ Holds semantic definitions (used to generate code from syntax trees)."""
    
    def __init__(self, defn_grammar_dir='defn_grammar/'):
        """ Initialize defn parser to prepare for parsing .defn specs."""
        defn_path = os.path.join(defn_grammar_dir, 'defn')      # defn.tokens, defn.syntax
        self.defn_parser = syntax.SyntaxParser(defn_path)
        self.defns = dict()     # dictionary of definitions: key is itemname, 
                                #   value is a list of DefnNode for this item

        
    def load(self, langpath):
        """ Load definitions from langpath.defn file."""
        # Use a SyntaxParser to load definitions into a parse tree.
        self.defn_tree = self.defn_parser.parse(langpath + '.defn')

        # Extract definitions from tree
        for definition in self.defn_tree.findall('definition'):
            signature = definition.first()
            sigkind = signature.first()
            name = sigkind.findtext()
            if sigkind.name == 'terminal':
                content = signature.find('STRING').text
            elif sigkind.name == 'nonterm':
                content = [arg.findtext() for arg in signature.findall('arg')]
                ### need to record subtype and index
            else:
                msg = 'Invalid signature type "%s" in %s definition' % (sigkind.name, name)
                raise Error().msg(msg)
            instructions = definition.find('instructions').findall('instruction')
            ### decode instructions here?
            self.defns.setdefault(name, []).append(DefnNode(content, instructions))

        
        
if __name__ == '__main__':
    defs = Definitions()

    lang = 'grammars/smaller'
    defs.load(lang)
    print defs.defns



