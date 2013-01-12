# grammar.py
# Modsplan grammar handling
# Copyright 2011-2013 by David H Post, DaviWorks.com.


from __future__ import print_function       # (using Python 2.7)

from collections import OrderedDict


quote_chars = "'" + '"'


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
        result = self.name + ': '
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
    def __init__(self, production, filename, linenum, flags=[]):
        self.items = production     # list of Item
        self.prefixes = None        # set of terminals that are possible prefixes
        self.filename = filename    # grammar file this production was loaded from
        self.linenum = linenum      # line number in grammar file
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
            if None in item_prefixes:
                if len(self.prefixes) > 0:
                    # something followed by nothing cannot be nothing
                    item_prefixes.remove(None)
                self.prefixes |= item_prefixes
                continue    # item can be empty, so may be more prefixes
            self.prefixes |= item_prefixes
            if item.quantifier not in '?*':
                break       # item cannot occur 0 times, so no more first terminals
        else:                           # end of alternate & still looking, so
            self.prefixes.add(None)     #   production may produce nothing
            

class Item:
    """ One element of a production, includes quantifier."""
    def __init__(self, element=None, quantifier='1'):
        """ Create item from element (string) and quantifier.)"""
        self.element = element
        self.quantifier = quantifier    # '1' (no quantifier), or '?', '+', '*'

    def __str__(self):
        return str(self.element) + self.quantifier.replace('1', '')

    def text(self):
        if self.isliteral():
            return self.element[1:-1]       # remove quotes
        else:
            return self.element

    def isliteral(self):                # extended by subclasses
        return self.element[0] in quote_chars

    def isterminal(self):
        return self.isliteral() or self.element.isupper()

    def get_prefixes(self, nonterms):
        """ Return set of possible first terminals generated by this item,
                given dictionary of nonterms for lookups.
        """
        if self.isterminal():
            prefix = self.text()
            prefixes = set([prefix])
        else:   # nonterminal
            nonterm = nonterms.get(self.element)
            if nonterm == None:
                raise Error().msg('Unrecognized nonterminal (%s)' % self.element)
            nonterm.find_prefixes(nonterms)
            prefixes = nonterm.prefixes
        return prefixes


class Error(Exception):
    """ Convenient error reporting."""
    def __init__(self, filename=None):
        self.filename = filename        # current filename (where errors found)
        self.message = ''

    def __str__(self):
        return self.message

    def msg(self, message, lineno=None, column=None):
        """ Add message. If line number specified, add it and filename to message;
            if column, insert that. Return self.
        """
        if lineno:
            message += ' in line %d' % lineno
            if column:
                message += ', column %s' % column
            message += ' of %s' % self.filename
        self.message = message
        return self


class Grammar:
    """ Holds a grammar."""
    def __init__(self, filename, make_item=Item):
        """ Load grammar from file (format defined by metagrammar).
            (make_item is a subclass of Item.)
        """
        self.filename = filename
        self.imported=[]                # list of imported filenames
        
#         self.imported=[filename]      # list of imported filenames
#                                   #   (start with current file to avoid import loops)
        
        self.nonterms = OrderedDict()   # dictionary of Nonterminals, keyed by name
            # ordered just to make show() output easier to read
        self.root = None                # last Nonterminal with a .root flag, if any
        self.err = Error(filename)      # set filename for error reporting
        self.make_item = make_item      # item constructor (extendable by subclasses)
        self.load_grammar(filename)
        
    
    def show(self):
        """ Display grammar. """
        if self.root:
            print('root is:')
            print(self.root.show())
            print('---------------\n')
        for nonterm in self.nonterms.values():
            print(nonterm.show())


    def show_prefixes(self):
        """ Return text table of prefixes of all nonterms."""
        text = '\nPrefixes:\n'
        for name, nonterm in sorted(self.nonterms.items()):
            text += '%s: %s\n' % (name, list(nonterm.prefixes))
        return text + '\n'
    
    
    def load_grammar(self, filename):
        """ Load grammar file (format defined by base.metagrammar).
            Store productions in self.nonterms.
            If grammar contains 'use' directives, import all needed files.
            Return the root Nonterminal, the last one loaded with a .root flag, or None.
            (To use multiple grammar files, create one file of 'use' directives.)
        """ 
        lineno = 0                  # line number of file
        needed = []                 # list of files needed (and not yet imported)
        in_preface = True           # true while lines are only comments and imports
        try:
            text = open(filename).read()
        except IOError, exc:
            raise self.err.msg('Error loading file ' + filename + '\n' + str(exc))
        lines = text.splitlines()
        for line in lines:
            lineno += 1                     # first line is line 1
            line = line.strip()
            if line == '':                  # skip blank line
                continue
            if line.startswith('#'):        # skip comment line
                continue
            if line.startswith('use '):     # files to be imported
                if not in_preface:
                    raise self.err.msg('"use" must appear before productions, error', lineno)
                for import_filename in line[4:].split(','):
                    import_filename = import_filename.strip()
                    if import_filename not in self.imported:
                        needed.append(import_filename)
                continue
            # line is not blank, comment, or use directive
            in_preface = False
            
### Possible infinite loop if two or more files "use" each other.
### How to prevent this?
###     Can we just add the current file to self.imported?
###         Does that prevent all chains?
###     Or do we have to remember chain of files, check for loop, give error?

### Any reference to a nonterm not in current file or its imports should give error.


#### Revise this to load separate grammar from each file, then merge them?
####    If so, how deal with references to nonterms only defined in imported file?

            while needed:   # files to import before parsing this grammar
                import_filename = needed.pop(0)
                self.load_grammar(import_filename)
                self.imported.append(import_filename)
            
            self.store_production(line, lineno, filename)
        self.load_items()       # replace raw strings of production with Item


    def store_production(self, line, lineno, filename):
        """ Parse a production, store in self.nonterms."""
        production = line.split()
# Would string items in grammar ever have spaces in them? (If so, don't split them.)
# If we want to save comments in terminals, don't split them.
        if len(production) < 3 or production[1] != '=>':
            raise self.err.msg(line + '\nSyntax error in grammar', lineno)
        nameflags = production[0].split('.')    # flags after name, separated by '.'
        name = nameflags[0]                     # remove any flags
        flags = nameflags[1:]
        nonterm = self.nonterms.get(name)
        if nonterm == None:                 # if not found, create it
            nonterm = Nonterminal(name)
            self.nonterms[name] = nonterm
        # Store raw strings for now; must create nonterms before we can point to them.
        alt = Alternate(production[2:], filename, lineno, flags)
        nonterm.alternates.append(alt)
        if 'root' in flags:
            self.root = nonterm

    
    def load_items(self):
        """ Replace item strings of a production with Items."""
        for nonterm in self.nonterms.values():
            for alt in nonterm.alternates:
                production = []                 # new production to replace raw strings
                for item in alt.items:
                    if item.startswith('#'):    # rest of production is comment, discard
                        break                   #### (only found if space before #)
                    quantifier = '1'
                    if item[-1] in '*+?':               # last char is a quantifier
                        quantifier = item[-1]
                        item = item[:-1]                # remove quantifier
                    self.check_item(item, quantifier, alt)
                    production.append(self.make_item(item, quantifier))
                alt.items = production          # replace raw production with cooked


    def check_item(self, item, quantifier, alt):
        """ Check string item, with quantifier, in alternate alt. (Extended by subclass.)"""
        if item[0] in quote_chars:              # terminal node: literal
            if item[0] != item[-1]:
                raise self.err.msg('Mismatched quotes in item (%s)' % item, alt.linenum)
        elif item.isupper():            # terminal, handled by subclasses
            pass
        elif item in self.nonterms:     # item should be name of nonterminal
            pass
        else:
            raise self.err.msg('Unrecognized item (%s)' % item, alt.linenum)


    

gfn = 'base.tokens'
gfn = 'tokens.metagrammar'      #### Error when "use" tries to add to existing nonterm.
gfn = 'base.metagrammar'
gfn = 'L0.syntax'

gr = None

def test(gfn=gfn):
    global gr
    gfn = 'grammars/' + gfn
    gr = Grammar(gfn)
    gr.show()

import sys

if __name__ == '__main__':
    if sys.argv[1:]:
        test(sys.argv[1])
    else:
        test()

