#!/usr/local/bin/python

# grammar.py
# Modsplan grammar handling
# Copyright 2011-2013 by David H Post, DaviWorks.com.


from collections import OrderedDict

import lineparsers


quote_chars = "'" + '"'
quantifiers = '*+?'
separators = '.,;:/|\&-='       # may be used with quantifier to separate repeating items
enable_cmd = 'enable '


class Nonterminal:
    """ Nonterminal node in grammar. """
    def __init__(self, name):
        self.name = name        # string
        self.alternates = []    # list of Alternates, productions for this nonterm
        self.prefixes = None    # set of terminals that are possible prefixes
                                
    def __str__(self):
        return self.name
    
    def show(self):
        """ Return string showing name with list of alternates."""
        result = self.name + ' => '
        indent = ' ' * len(result)
        return result + ('\n' + indent).join(map(str, self.alternates)) + '\n'

    def find_prefixes(self, nonterms):
        """ Compute set of all possible first terminals generated from this Nonterminal,
                given dictionary of nonterms for lookups.
            Result saved in self.prefixes.
        """
        if self.prefixes:
            return              # already computed
        self.prefixes = set()
        for alt in self.alternates:
            alt.find_prefixes(nonterms)
            self.prefixes |= alt.prefixes


class Alternate:
    """ Holds items of one production. """    
    def __init__(self, production, location, flags=None):
        self.items = production     # list of Item
        self.prefixes = None        # set of terminals that are possible prefixes
        self.location = location    # lineparsers.Location of production: filepath, linenum...
        if flags == None:
            flags = []
        self.flags = flags          # list of attribute strings
    
    def __str__(self):
        return ' '.join(map(str, self.items))
    
    def find_prefixes(self, nonterms):
        """ Compute set of all possible first terminals generated from this Alternate,
                given dictionary of nonterms for lookups.
            Result saved in self.prefixes.
        """
        if self.prefixes:
            return                  # already computed
        self.prefixes = set()
        for item in self.items:
            item_prefixes = item.get_prefixes(nonterms)
            self.prefixes |= item_prefixes
            if '' in item_prefixes:
                continue    # item can be empty, so may be more prefixes
            if item.quantifier not in '?*':
                break       # item cannot occur 0 times, so no more first terminals
        else:   # end of alternate & still looking, so production may produce nothing
            self.prefixes.add('')
            

class Item:
    """ One item of a production, includes quantifier. Extended by subclasses."""
    
    def __init__(self, element, quantifier='1', separator=''):
        """ Create item from element (string), optional quantifier, separator.
            An element must be one of:
                terminal:
                    literal: first and last char must be same quotechar (' or ")
                    tokenkind: all uppercase chars
                nonterminal: any other string (normally lowercase chars).
        """
        self.element = element
        self.quantifier = quantifier    # '1' (no quantifier), or '?', '+', '*'
        self.separator = separator      # one of separators, or ''

    def __str__(self):
        return str(self.element) + self.separator + self.quantifier.replace('1', '')

    def strq(self):
        """ Represent item as string with quantifier."""
        return str(self.element) + self.quantifier.replace('1', '')

    def text(self):
        if self.isliteral():
            return self.element[1:-1]       # remove quotes
        else:
            return self.element

    def isliteral(self):
        return self.element[0] in quote_chars

    def isterminal(self):           # extended by subclasses
        return self.isliteral() or self.element.isupper()

    def get_prefixes(self, nonterms):
        """ Return set of possible first terminals generated by this item,
                given dictionary of nonterms for lookups.
        """
        if self.isterminal():
            prefix = self.text()
            return set([prefix])        ## Python 2.7+ can use {prefix}
        else:   # nonterminal
            nonterm = nonterms[self.element]    # must be in nonterms, checked when created
            nonterm.find_prefixes(nonterms)
            return nonterm.prefixes


class Grammar:
    """ Holds a grammar."""
    def __init__(self, filepath, make_item=Item):
        """ Load grammar from file (format defined by metagrammar).
            (make_item must be a subclass of Item.)
        """
        self.filepath = filepath
        self.nonterms = OrderedDict()   # dictionary of Nonterminals, keyed by name
        self.root = None                # last Nonterminal with a .root flag, if any
        self.options = []               # list of (string) options from enable commands
        self.make_item = make_item      # item constructor (extendable by subclasses)
        self.load_grammar(filepath)
        
    
    def show(self):
        """ Display grammar. """
        print
        for nonterm in self.nonterms.values():
            if nonterm == self.root:
                print '(root:)'
            print nonterm.show()


    def show_prefixes(self):
        """ Return text table of prefixes of all nonterms."""
        lines = ['\nPrefixes:\n']
        for name, nonterm in self.nonterms.items():
            lines += ['%s: %s' % (name, ' '.join(nonterm.prefixes))]
        lines.sort()
        return '\n'.join(lines) + '\n'
    
    
    def load_grammar(self, filepath):
        """ Load grammar file, store productions (format defined by base.metagrammar).
            'enable' commands set options.
            'use' commands include other files (see lineparsers.py).
            Last nonterminal with suffix '.root' is recorded as root.
        """
        lines = lineparsers.LineInfoParser(filepath)
        for line in lines:
            if line.startswith(enable_cmd):
                option = line[len(enable_cmd):].strip()
                if option.isalnum():    # if not alphanumeric, process line as a production
                    self.options.append(option.lower())
                    continue
            line = line.strip()
            if line and not line.startswith('#'):   # skip blank and comment lines
                self.store_production(line, lines.location)
        self.load_items()       # replace raw strings of production with Item


    def store_production(self, line, location):
        """ Parse a production, store in self.nonterms.
            Location object contains filepath and line number for error reporting."""
        production = line.split()
# Would literal items in grammar ever have spaces in them? (If so, don't split them.)
# If we want to save comments in terminals, don't split them.
        if len(production) < 3 or production[1] != '=>':
            raise location.error(line + '\nSyntax error in grammar')
        nameflags = production[0].split('.')    # flags after name, separated by '.'
        name = nameflags[0]                     # remove any flags
        flags = nameflags[1:]
        nonterm = self.nonterms.setdefault(name, Nonterminal(name))     # create if not found
        # Store raw strings for now; must create nonterms before we can point to them.
        alt = Alternate(production[2:], location, flags)
        nonterm.alternates.append(alt)
        if 'root' in flags:
            self.root = nonterm

    
    def load_items(self):
        """ Replace item strings of a production with Items."""
        for nonterm in self.nonterms.values():
            for alt in nonterm.alternates:
                production = []                 # new production to replace raw strings
                literal_next = False            # if true, next item must be literal
                for item in alt.items:
                    if item.startswith('#'):    # rest of production is comment, discard
                        break                   #   (only if space before #)
                    if literal_next and (item[0] not in quote_chars):
                        message = 'Literal or end of line must follow character class P*'
                        raise alt.location.error(message)
                    literal_next = (item == 'P*')       # literal must follow 'P*'
                    quantifier = '1'
                    separator = ''
                    if item[-1] in quantifiers:
                        quantifier = item[-1]
                        item = item[:-1]                # remove quantifier
                        if item and item[-1] in separators:
                            separator = item[-1]
                            item = item[:-1]                # remove separator
                    self.check_item(item, quantifier, alt)
                    production.append(self.make_item(item, quantifier, separator))
                alt.items = production          # replace raw production with cooked


    def check_item(self, item, quantifier, alt):
        """ Check string item, with quantifier, in alternate alt. (Extended by subclass.)"""
        if item == '':
            raise alt.location.error('Misplaced quantifier')
        if item[0] in quote_chars:      # terminal node: literal
            if item[0] != item[-1]:
                raise alt.location.error('Mismatched quotes in item (%s)' % item)
            if len(item) < 3:
                raise alt.location.error('Empty literal not allowed (%s)' % item)
        elif item.isupper():            # terminal, handled by subclasses
            pass
        elif item in self.nonterms:     # item should be name of nonterminal
            pass
        else:
            raise alt.location.error('Unrecognized item (%s)' % item)


gfn = 'base.tokens'
gfn = 'tokens.metagrammar'
gfn = 'base.metagrammar'
gfn = 'L0.syntax'

gr = None

def test(gfn=gfn):
    global gr
    gfn = 'modspecs/' + gfn
    gr = Grammar(gfn)
    gr.show()

import sys

if __name__ == '__main__':
    try:
        if sys.argv[1:]:
            test(sys.argv[1])
        else:
            test()
    except lineparsers.Error as exc:
        print exc
