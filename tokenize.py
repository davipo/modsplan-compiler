# tokenize.py
# Modsplan tokenizer
# Copyright 2011-2012 by David H Post, DaviWorks.com.


from collections import namedtuple

import grammar


Token_t = namedtuple('Token', 'name, text, linenum, column')
""" name is the (string) name for the kind (the category) of the token.
    text is the string of the token.
    linenum is the line in the source where found.
    column is the column in the source of the first character of the token.
"""

class Token(Token_t):

    def __str__(self):
        """ If no text, return name. If no name, return quoted text.
            If both, return name(text)."""
        if self.name:
            result = self.name
            if self.text:
                result += '(' + self.text + ')'
        else:
            result = "'" + self.text + "'"
        return result


class TokenGrammar(grammar.Grammar):
    """ Defines token syntax, kinds of tokens. Token definitions read from file."""
    def __init__(self, filename):
        """ Load token grammar from file (format defined by tokens.metagrammar).
            Compute prefixes, and possible token kinds for each prefix.
        """
        grammar.Grammar.__init__(self, filename, TokenItem)
        self.kinds = []                 # list of token Nonterminals
        self.prefix_map = dict()        # maps prefix to list of kind.name
        
        for name, nonterm in self.nonterms.items():
            if name.isupper():          # uppercase name is a token kind
                self.kinds.append(nonterm)
        
        # Compute possible prefix chars for each kind of token
        for kind in self.kinds:
            kind.find_prefixes(self.nonterms)       # stores prefixes in kind
            # Compute possible token kinds for each prefix.
            for prefix in kind.prefixes:
                first_char = prefix[0]      # tokenizer uses one char prefix
                if first_char not in self.prefix_map:
                    self.prefix_map[first_char] = []
                self.prefix_map[first_char].append(kind.name)
    

    def check_item(self, item, quantifier, alt):
        """ Check string item, with given quantifier, in alternate alt."""
        # Check for error if (string) item is a character class.
        if item.isupper() and len(item) == 1:
            if item == 'P' and quantifier != '*':
                message = 'Character class P must be used with *, error'
                raise self.err.msg(message, alt.linenum)
            ## Check for valid character class (L, U, D, P) here?
        else:
            item = grammar.Grammar.check_item(self, item, quantifier, alt)


class TokenItem(grammar.Item):
    def __init__(self, elem=None, quant='1'):
        grammar.Item.__init__(self, elem, quant)
        
    def ischarclass(self):
        return len(self.element) == 1 and self.element.isupper()

    def isterminal(self):
        return self.isliteral() or self.ischarclass()


class Error(grammar.Error):
    """ Convenient error reporting."""

    def msg(self, message, loc=None, column=None):
        """ If loc is Token, extract line number & column; else assume loc is line number.
            If line number specified, add it and filename to message; if column, insert that.
            Otherwise just use message.
        """
        if isinstance(loc, Token):
            lineno, column = loc.linenum, loc.column
        else:
            lineno = loc
        return grammar.Error.msg(self, message, lineno, column)
        

class Tokenizer:
    """ Configurable tokenizer. Reads a token specification grammar,
    then parses source text into tokens, as defined by the grammar.
    """
    def __init__(self, grammar_filename):
        """ Create tokenizer from grammar file (format defined in tokens.metagrammar).
            The grammar defines the syntax and kinds of tokens.
            If grammar contains 'use' directives, import all needed files.
            To use multiple grammar files, create one file of 'use' directives.
        """
        self.source_filename = None                     # set in token_generator
        self.tokendef = TokenGrammar(grammar_filename)  # load token definitions

                    
    def names(self):
        """ Return list of token kind names."""
        return [kind.name for kind in self.tokendef.kinds]

    def prefixes(self):
        """ Return text table of prefixes for each token kind."""
        text = '\nPrefixes for token kinds:\n'
        for kind in self.tokendef.kinds:
            text += '%s: %s\n' % (kind.name, list(kind.prefixes))
        return text + '\n'

    def token_generator(self, filename, tabsize=4):
        """ A generator method, returns an iterator of Token from given source file.
            tabsize is # of spaces indent per tab char, to produce accurate column #s.
        """
        self.source_filename = filename
        err = Error(filename)
        try:
            source = open(filename).read()
        except IOError, exc:
            raise err.msg('Error loading file ' + filename + '\n' + str(exc))
        lines = source.splitlines()

        # First nonblank line beginning with \t or space sets tab.
        tab = first_indent(lines)
        if tab[:1] == ' ':
            tabsize = len(tab)
        
        # Read lines from top, tokenize
        lineno = 0              # line number
        indentlevel = 0
        for line in lines:
            lineno += 1             # first line is line 1

            # Check indentation level
            # Only if language is indentation-sensitive? (like python)
            level, extra = indentation(line, tab)
            if extra:               # extra spaces
                raise err.msg('Inconsistent indentation', lineno)
            if level == indentlevel + 1:
                indentlevel += 1
                yield(Token('INDENT', '', lineno, 1 + tabsize * indentlevel))
            else:
                while indentlevel > level:
                    indentlevel -= 1
                    yield(Token('DEDENT', '', lineno, 1 + tabsize * indentlevel))

            col = 0             # column of line
            viewcol = 1         # column as viewed in source (1-origin, expand tabs)
            while col < len(line):
                char = line[col]
                chclass = charclass(char)
                kindnames = self.tokendef.prefix_map.get(chclass, [])   # empty if not found
                for kindname in kindnames:
                    kind = self.tokendef.nonterms[kindname]
                    length = self.match(line[col:], kind)
                    if length > 0:
                        # match found, length is number of chars matched
                        yield(Token(kindname, line[col:col + length], lineno, viewcol))
                        col += length
                        viewcol += length
                        break           # look for next token
                else:  # no match found for any kind starting with char
                    if char not in ' \t':       # skip space, tab
                        yield(Token('', char, lineno, viewcol))     # operator, punctuation
                    col += 1
                    viewcol += tabsize if char == '\t' else 1
            yield(Token('NEWLINE', '', lineno, viewcol))        # mark end of line
        while indentlevel > 0:        # close indented blocks
            indentlevel -= 1
            yield(Token('DEDENT', '', lineno + 1, 1 + tabsize * indentlevel))


    def match(self, text, nonterm):
        """ Look for match with nonterm at start of text.
            Return number of chars matched (-1 if no match).
        """
        if debug > 2:
            print 'match nonterm %s with "%s":' % (nonterm.name, text)
        col = 0             # index to text
        for alt in nonterm.alternates:
            skip = False
            for item in alt.items:
                if item.ischarclass() and item.text() == 'P':       # assumes P*
                    skip = True
                    continue            # on to next item
                length = self.match_item(text[col:], item, skip, alt)
                if length == -1:        # if item fails to match
                    col = 0                 # reset column
                    break                   # try next alternate
                skip &= (length == 0)   # skip until we match a terminal literal
                col += length
                assert col <= len(text)     # no overshoot I hope
            else:               # end of alt, it matched
                if skip:            # P* was last item in alternate,
                    col = len(text)     # so it matches the rest of the text
                return col
        return -1   # end of alternates, failed to match


    def match_item(self, text, item, skip, alt):
        """ Look for match with item at start of text, return # of chars matched,
            or -1 if no match. If skip, skip chars until item is found, or end.
            Use alt to report error location.
        """
        if debug > 2:
            print '   match_item %s with "%s"' % (item, text)
        col = 0
        err = Error(self.tokendef.filename)
        quant = item.quantifier
        item_text = item.text()

        if skip:
            # last item was character class P*, so match any chars before this item
            if not item.isliteral():
                message = 'Terminal literal or EOL must follow character class P*'
                raise err.msg(message, alt.linenum)
            col = text.find(item_text)
            if col == -1:       # item not found; but it may have zero occurrences, so
                col = 0         #   don't fail, just no progress (try next item)
            else:
                col += len(item_text)   # found it, move past it
            return col            
        
        while col < len(text):
            length = -1         # failure unless otherwise determined
            if item.ischarclass():
                if item_text == charclass(text[col]):
                    length = 1
            elif item.isliteral():
                if text[col:].startswith(item_text):
                    length = len(item_text)
            else:   # item must be a nonterminal
                nonterm = self.tokendef.nonterms[item_text]
                length = self.match(text[col:], nonterm)    # (0 is a match)
            # we have a match unless length == -1
            if debug > 3:
                print '  ', col, length, item
            # handle quantifier repetitions
            if quant in '?*' or (quant == '+' and col > 0):
                # can do zero occurrences, so don't need to match
                length = max(0, length)     # 0 is worst case
            if quant not in '*+':   # can't repeat
                return length       # first time through, col == 0
            if length <= 0:
                return col
            col += length
        return col
                
    
def charclass(char):
    """ Return character class of char. See base.metagrammar for character classes."""
    if char.islower():
        return 'L'
    elif char.isupper():
        return 'U'
    elif char.isdigit():
        return 'D'
    else:
        return char     # char is its own class


def first_indent(lines):
    """ Scan list of text lines, return first indent found (tab or spaces). """
    tab = ''
    for line in lines:
        if line.strip() == '':
            continue                        # skip blank line
        if line.startswith('\t'):
            tab = '\t'
            break
        elif line.startswith(' '):
            numspaces = lcount(line, ' ')
            tab = ' ' * numspaces           # tab is some spaces
            break
    return tab

def lcount(line, chars):
    """ Count the number of consecutive characters in chars at beginning of line."""
    return len(line) - len(line.lstrip(chars))

def indentation(line, tab):
    """ Return (indentation level, remainder) of line, using tab string as indent. """
    if tab:
        return divmod( lcount(line, tab[0]), len(tab) )
    else:
        return 0, 0
    
## (Use a utility program to clean up indents in files?)
                

def reassemble(tokens):
    """ Return a string of tokens in lines similar to the original source."""
    level = 0
    nl = True
    result = ''
    lastkind = None
    for tkn in tokens:
        kind, string = tkn[0:2]
        if kind == 'NEWLINE':
            if nl == True:
                result += '\n'
            nl = True
        elif kind == 'INDENT':
            level += 1
        elif kind == 'DEDENT':
            level -= 1
        else:
            if nl:
                result += '\n'
                if kind != 'COMMENT':
                    result += ' ' * 4 * level
            if kind == 'COMMENT':
                if not nl:
                    result += ' \t\t'
                result += string
            elif kind == 'RELATION' or kind.endswith('_OP'):
                result += ' ' + string + ' '
            elif kind == 'ASSIGN':
                if lastkind.endswith('_OP'):
                    result = result.rstrip()    # remove last space
                else:
                    result += ' '
                result += string + ' '
            else:
                if kind == 'NAME' and lastkind == 'NAME':
                    result += ' '
                result += string
                result += ' ' * (string in ',')
            nl = False
        lastkind = kind
    return result



def test(filename):
    global t
    tokens = t.token_generator(filename)
    print 'Tokens from ' + filename + ':\n'
    for tkn in tokens:
        print tkn


debug = 1

if __name__ == '__main__':
    t = Tokenizer('grammars/L0.tokens')
    print t.prefixes(),
    for p, tn in sorted(t.tokendef.prefix_map.items()):
        print '%3s: %s' % (p, tn)
    print
    
    nts = t.tokendef.nonterms
    kname = nts['NAME']
    
    kinds = t.tokendef.kinds
    
    ##print t.match('< 3', nts["RELATION"])
    
    fn = 'sample.lang'
    # fn = 'snape.lang'
    ##fn = 'sample.py'
    ##fn = 'reassemble.py'
    
    fn = 'sample source/' + fn
    
    tokens = t.token_generator(fn)
    tokens = list(tokens)
    if debug == 1:
        print 'Tokens from ' + fn + ':\n'
        for tkn in tokens:
            print tkn   
    ra = reassemble(tokens)
    print ra

