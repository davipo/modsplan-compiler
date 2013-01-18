# parsetree.py
# Modsplan parse tree
# Copyright 2013 by David H Post, DaviWorks.com.


indentation = ' ' * 4       # string to display one level of indentation


def new(name):
    """ Return new empty tree, with name on root node."""
    return NonterminalNode(name)


class BaseNode:
    """ Base class for a node of the parse tree."""
    def __init__(self, name):
        self.name = name                # name of nonterminal or terminal
        self.level = 0                  # depth of node in tree


    def indent(self):
        """ Return string of indentation to level of node."""
        return indentation * self.level


class TerminalNode(BaseNode):
    """ A terminal node of the parse tree; contains text."""
    def __init__(self, name, text):
        BaseNode.__init__(self, name)
        self.text = text                # terminal text


    def isterminal(self):
        return True


    def __str__(self):
        return self.name + '(' + self.text + ')'


    def show(self):
        """ Return string to display node at its indent level."""
        return self.indent() + str(self) + '\n'


class NonterminalNode(BaseNode):
    """ A nonterminal node of the parse tree; contains a list of child nodes."""
    def __init__(self, name):
        BaseNode.__init__(self, name)
        self.children = []


    def isterminal(self):
        return False


    def __str__(self):
        return self.name + '[' + ', '.join([str(child) for child in self.children]) + ']'


    def add_child(self, name, text=None):
        """ Append child node to this node's list of children. 
            If text is given, append terminal node, else append nonterminal."""
        if text:
            child = TerminalNode(name, text)
        else:
            child = NonterminalNode(name)
        child.level = self.level + 1
        self.children.append(child)
        return child
        

    def remove_child(self):
        """ Remove last child."""
        del self.children[-1]
        

    def remove_children(self):
        del self.children[:]
    

    def show(self):
        """ Return display (as string) of parse tree starting at this node."""
        result = self.indent() + self.name + '\n'
        for node in self.children:
            result += node.show()
        return result

