# defn.py
# Modsplan .defn parser
# Copyright 2011-2013 by David H Post, DaviWorks.com.


import syntax
from grammar import Error


class DefnNode:
    
    def __init__(self, content, instructions):
        self.text = None                    # text if terminal node
        self.args = None                    # list of arguments if nonterminal
        self.instructions = instructions    # list of code generation instructions
        if isinstance(content, str):
            self.text = content
        elif isinstance(content, list):
            self.args = content
        else:
            raise Error().msg('Invalid content for DefnNode %s' % name)


class Definitions:
    """ Holds semantic definitions (used to generate code from syntax trees)."""
    
    def __init__(self):
        self.defns = dict()     # dictionary of definitions: key is itemname, 
                                #   value is a list of DefnNode for this item
        self.defn_parser = syntax.SyntaxParser('grammars/defn')

        
    def load(self, langname):
        """ Load definitions from langname.defn file."""
        # Use a SyntaxParser to load definitions into a parse tree.
        self.defn_tree = self.defn_parser.parse(langname + '.defn')

        # Extract definitions from tree
        for definition in self.defn_tree.findall('definition'):
            signature = definition.first()
            sigkind = signature.first()
            name = sigkind.findtext()
            if sigkind.name == 'terminal':
                content = signature.find('STRING').text
            elif sigkind.name == 'nonterm':
                content = [arg.findtext() for arg in signature.findall('arg')]
            else:
                msg = 'Invalid signature type "%s" in %s definition' % (sigkind.name, name)
                raise Error().msg(msg)
            instructions = definition.find('instructions').findall('instruction')
            ### decode instructions here?
            self.defns.setdefault(name, []).append(DefnNode(content, instructions))

        
        
        

defs = Definitions()

lang = 'grammars/smaller'
defs.load(lang)
print defs.defns



