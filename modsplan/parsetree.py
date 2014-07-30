# parsetree.py
# Modsplan parse tree
# Copyright 2013 by David H Post, DaviWorks.com.


indent_size = 3
indent1 = ' ' * indent_size             # string to display one level of indentation
indent2 = '|' + indent1[1:]             # every other indent contains a vertical bar
indentation = indent1 * 2 + (indent2 + indent1) * 40    # (enough for 82 indent levels)


def new(name, debug_flags=''):
    """ Return new empty tree, with name on root node."""
    return NonterminalNode(name, debug_flags)


class BaseNode:
    """ Base class for a node of the parse tree."""
    def __init__(self, name, debug_flags):
        self.name = name                # name of nonterminal or terminal
        self.debug = debug_flags
        self.level = 0                  # depth of node in tree
        self.location = None            # (lineparsers.Location) where found in source text 
        self.used = False               # to keep track of nodes already compiled

    def set_location(self, token):
        """ Set location in source code from token."""
        if not self.location:       # set once only
            self.location = token.location

    def indent(self):
        """ Return string of indentation to level of node."""
        location = ''
        if 'n' in self.debug:
            location = '%2d %2d ' % (self.location.linenum, self.location.column)
        return location + indentation[len(location):self.level * indent_size]

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
    def __init__(self, token, debug_flags):
        BaseNode.__init__(self, token.name, debug_flags)
        self.text = token.text              # terminal text
        self.set_location(token)

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

    def nextchild(self, name=None, use=True, loc=None):
        message = 'Terminal node "%s" has no children' % self.name
        if name:
            message += ' (seeking name "%s")' % name
        raise (loc if loc else self).location.error(message)


class NonterminalNode(BaseNode):
    """ A nonterminal node of the parse tree; contains a list of child nodes."""
    def __init__(self, name, debug_flags):
        BaseNode.__init__(self, name, debug_flags)
        self.children = []
        # location must be set by caller

    def isterminal(self):
        return False

    def __str__(self):
        return self.name + '[' + ', '.join([str(child) for child in self.children]) + ']'
    
    def numchildren(self):
        return len(self.children)

    def add_child(self, thing):
        """ Append child node to this node's list of children.
            If thing is a string, make a nonterminal node named with it;
            else assume thing is a token, make a terminal node with it."""
        if isinstance(thing, str):
            child = NonterminalNode(thing, self.debug)
        else:
            child = TerminalNode(thing, self.debug)
        child.level = self.level + 1
        self.children.append(child)
        return child
        
    def remove_child(self):
        """ Remove last child."""
        del self.children[-1]
        
    def remove_children(self, numchildren=None):
        """ Remove first numchildren children, or all if number not given."""
        del self.children[:numchildren]
        
    def keep_children(self, numchildren):
        """ Keep first numchildren children, discard the rest."""
        del self.children[numchildren:]
        
    def show(self):
        """ Return display (as string) of parse tree starting at this node."""
        result = self.indent() + self.name + '\n'
        for node in self.children:
            result += node.show()
        return result

    def nextchild(self, name=None, use=True, loc=None):
        """ Return next unused child; if name, next matching name; if none, raise error;
            mark child used. If use false, ignore use status, return first (matching) child.
            Optional loc gives node whose location to report in case of error."""
        for child in self.children:
            if (use and child.used) or (name and child.name != name):
                continue
            else:
                child.used = child.used or use
                return child
        # not found
        message = 'Node "%s" has no%s child' % (self.name, ' unused' if use else '')
        if name:
            message += ' with name "%s"' % name
        raise (loc if loc else self).location.error(message)

    def firstchild(self, name=None, loc=None):
        """ Return first child; if name, first matching name; if none, raise error.
            Optional loc gives node whose location to report in case of error."""
        return self.nextchild(name, use=False, loc=loc)

    def find(self, name):
        """ Return first node with name in preorder traversal from this node, or None."""
        if self.name == name:
            return self
        else:
            result = None
            for child in self.children:
                result = child.find(name)
                if result is not None:
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
                if text is not None:
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
        
