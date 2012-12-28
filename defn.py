# Modsplan defn parser
# author: David Post
# date: 2011-09-21

import syntax



class DefnNode:
    
    def __init__(self, name, args, instructions):
        self.name = name                    # name of node (nonterminal or terminal)
        self.args = args                    # list of arguments (children of node)
        self.instructions = instructions    # list of code generation instructions


class Defn:
    """ Read and store .defn files (used to generate code from syntax trees)."""
    
    def __init__(self):
        self.defns = dict()     # dictionary of definitions
                                #   key is a list of strings: name followed by args
                                #   value is a list of instructions
        self.defn_parser = syntax.SyntaxParser('grammars/defn')

        
    def load(self, filename):
        """ Load definitions from file.
            Store definitions in self.defns.
        """
        
        # Use a SyntaxParser to load definitions into a syntax tree.
        self.defn_tree = self.defn_parser.parse(filename)

        
        # Extract definitions from tree into self.defns.
        
        

defs = Defn()

dfile = 'grammars/base.defn'
defs.load(dfile)
defs.defn_tree.show()
