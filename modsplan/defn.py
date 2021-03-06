# defn.py
# Modsplan .defn parser
# Copyright 2011-2013 by David H Post, DaviWorks.com.

import os.path

import syntax


class DefnNode:  #### not used ####
    
    def __init__(self, instructions):
        self.instructions = instructions    # list of code generation instructions
        ### any other data? If not, we don't need this class.

    def __str__(self):
        return self.instructions.show()


def remove_quotes(text):
    if text[0] in ('"', "'"):
        text = text[1:-1]
    return text


class Definitions:
    """ Holds semantic definitions (used to generate code from syntax trees)."""
    
    def __init__(self, defn_grammar_dir='defn_grammar/'):
        """ Initialize defn parser to prepare for parsing .defn specs."""
        defn_path = os.path.join(defn_grammar_dir, 'defn')
        self.defn_tree = None   # parse tree of last definitions loaded; set by load()
        self.defn_parser = syntax.SyntaxParser(defn_path)   # uses defn.tokens, defn.syntax
        self.defns = dict()     # Dictionary of definitions: 
                                #   key is signature (list of strings for name and args), 
                                #   value is a list of instructions for this defn.
        
    def load(self, langpath):
        """ Load definitions from langpath.defn file."""
        # Use a SyntaxParser to load definitions into a parse tree.
        self.defn_tree = self.defn_parser.parse(langpath + '.defn', enable_imports=True)

        # Extract definitions from tree
        self.defns.clear()
        for definition in self.defn_tree.findall('definition'):
            signature = self.make_signature(definition.firstchild())
            instructions = definition.firstchild('instructions').findall('instruction')
            self.defns[signature] = [instr for instr in instructions if instr.children]
                # remove empty instructions

    def make_signature(self, signode):
        ### move outside class?
        if signode.firstchild().name == 'nonterm':
            signature = [signode.findtext()]
            signature += [childname(node) for node in signode.findall('child')]
        else:   # 'terminal'
            signature = [node.findtext() for node in signode.children
                            if node.name != 'COMMENT']
        signature = map(remove_quotes, signature)
        ### need to get subtypes
        return tuple(signature)

    def get_defn(self, source_node):
        """ Return a list of instructions for the defn matching source_node, or None."""
        signature = [source_node.name]
        if source_node.isterminal():
            signature.append(source_node.text)
        else:
            for child in source_node.children:
                if child.name != 'COMMENT':
                    signature.append(child.name)
        return self.defns.get(tuple(signature))
    
    def show(self, sigs_only=True):
        """ Return string display of sorted definitions."""
        display = '\n'
        sigs = self.defns.keys()
        sigs.sort()
        for sig in sigs:
            display += sig_str(sig) + '\n'
            if not sigs_only:
                display += '\n'.join([ instr.show() for instr in self.defns[sig] ]) + '\n'
        return display + '\n'

    def first_alternate(self, nonterm_name):
        """ Return first Alternate for named nonterm in defn syntax.
            Used to access the location of an error in defn spec."""
        return self.defn_parser.syntax.nonterms[nonterm_name].alternates[0]


def sig_str(sig):
    return sig[0] + '(' + ' '.join(sig[1:]) + ')'


def childname(child):
    """ Given child node in defn tree (or its parent, if single child), 
        return name of child with quantifier, if any."""
    name = child.findtext()
    qnode = child.find('QUANTIFIER')
    return name + (qnode.findtext() if qnode else '')


if __name__ == '__main__':
    defs = Definitions()
    lang = 'modspecs/L0'
    defs.load(lang)
    print defs.show()


