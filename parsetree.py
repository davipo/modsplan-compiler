# parsetree.py
# Modsplan parse tree
# Copyright 2013 by David H Post, DaviWorks.com.


from grammar import Error


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


    def find(self, name):
        """ Return self if name matches. Extended by subclass."""
        if self.name == name:
            return self
        else:
            return None


    def findall(self, name):
        """ Return a list of nodes with specified name. Extended by subclass."""
        if self.name == name:
            return [self]
        else:
            return []


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


    def findtext(self):
        """ Return text of this terminal."""
        return self.text


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


    def first(self, name=None):
        """ Return first child; if name, first matching name; if none, raise error."""
        err = ''
        i = 0               # first child
        if self.children:
            if name:
                try:
                    i = self.children.index(name)
                except ValueError:
                    err = ' with name "%s"' % name
        else:
            err = ' '
        if err:
            message = 'Node %s has no first child' % self.name
            raise Error().msg(message + err)
        else:
            return self.children[i]
            

    def find(self, name):
        """ Return first node with name in preorder traversal from this node."""
        if self.name == name:
            return self
        else:
            result = None
            for child in self.children:
                result = child.find(name)
                if result:
                    break
            return result

    
    def findtext(self):
        """ Return text of first terminal found in preorder traversal from this node,
            or None if none found."""
        text = None
        for child in self.children:
            if child.isterminal():
                text = child.text
                break
            else:
                text = child.findtext()
                if text:
                    break
        return text

        
    def findall(self, name):
        """ Traverse tree from this node in preorder, 
            return a list of all nodes with specified name. (Don't search below those.)"""
        if self.name == name:
            return [self]
        else:
            result = []
            for child in self.children:
                result.extend(child.findall(name))
            return result
        
