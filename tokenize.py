# tokenize.py
# Modsplan tokenizer
# Copyright 2011-2013 by David H Post, DaviWorks.com.


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
        
        # nonterminals with uppercase names specify a kind of token
        # self.nonterms is an OrderedDict, so this preserves order of definition
        self.kinds = [nonterm for name, nonterm in self.nonterms.items() if name.isupper()]
                        
        # Compute possible prefix character classes for each kind of token.
        #   prefix_map[char_class] is a list of kinds that can start with the character class.
        #   These lists preserve the order of tokenkinds in .tokens specification.
        self.prefix_map = dict()
        for kind in self.kinds:
            kind.find_prefixes(self.nonterms)       # stores prefixes in kind
            # Compute list of possible token kinds for each prefix's character class
            kind.prefixes.discard(None)     ## should not have None, but in case (give error?)
            for prefix in kind.prefixes:
                # if prefix is already a character class (1 uppercase letter) just use it
                #       (needed for keywords and bool_ops)
                ###     Buggy if we have any uppercase keywords
                chrclass = prefix if TokenItem(prefix).ischarclass() else charclass(prefix[0])
                # Keep lists of kinds ordered as in token grammar
                chrclass_kinds = self.prefix_map.setdefault(chrclass, [])   # new list if none
                if kind not in chrclass_kinds:
                    chrclass_kinds.append(kind)
    

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
    def __init__(self, elem=None, quant='1', sep=''):
        grammar.Item.__init__(self, elem, quant, sep)
        
    def ischarclass(self):
        """ Is item a character class specifier (one uppercase letter)?"""
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
        self.tokendef = TokenGrammar(grammar_filename)  # load token definitions
        self.source_filename = None                     # set in get_tokens()
        self.err = None                     # source error reporter, set in get_tokens()

                    
    def names(self):
        """ Return list of token kind names."""
        return [kind.name for kind in self.tokendef.kinds]

    def prefixes(self):
        """ Return text table of prefixes for each token kind."""
        text = '\nPrefixes for token kinds:\n'
        for kind in self.tokendef.kinds:
            text += '%s: %s\n' % (kind.name, list(kind.prefixes))
        return text + '\n'

    def get_tokens(self, filename, tabsize=4):
        """ Tokenize source from filename, return a list of Token.
            tabsize is # of spaces per tab char, to report accurate column #s.
        """
        self.source_filename = filename
        self.err = Error(filename)
        try:
            source = open(filename).read()
        except IOError, exc:
            raise self.err.msg('Error loading file ' + filename + '\n' + str(exc))
        lines = source.splitlines()

        # First nonblank line beginning with \t or space sets tab.
        tab = first_indent(lines)       # '\t' or a string of spaces
        if ' ' in tab:
            tabsize = len(tab)
        
        # Read lines from top, tokenize
        tokens = []
        lineno = 0              # line number
        indentlevel = 0
        for line in lines:
            lineno += 1             # first line is line 1
            
            indentlevel = self.process_indents(line, lineno, indentlevel, tab, tabsize, tokens)

            col = 0             # column of line
            viewcol = 1         # column as viewed in source (1-origin, expand tabs)
            while col < len(line):
                char = line[col]
                chclass = charclass(char)
                # search for match among tokenkinds that can begin with this char class
                kinds = self.tokendef.prefix_map.get(chclass, [])   # empty list if none
                for kind in kinds:
                    length = self.match(line[col:], kind)
                    if length > 0:
                        # match found, length is number of chars matched
                        text = line[col:col + length]
                        tokens.append(Token(kind.name, text, lineno, viewcol))
                        col += length
                        viewcol += length
                        break           # look for next token
                else:  # no match found for any kind starting with char
                    if char not in ' \t':       # skip space, tab
                        tokens.append(Token('', char, lineno, viewcol))     # punctuation
                    col += 1
                    viewcol += tabsize if char == '\t' else 1
            tokens.append(Token('NEWLINE', '', lineno, viewcol))    # mark end of line

        # close indented blocks
        self.process_indents('', lineno + 1, indentlevel, tab, tabsize, tokens)
        return tokens


    def process_indents(self, line, lineno, indentlevel, tab, tabsize, tokens):
        """ Check indentation level, append indent & dedents to tokens."""
        ### Only if language is indentation-sensitive? (like Python)
        level, extra = divmod( lcount(line, tab[0]), len(tab) )
        if extra:               # extra spaces
            raise self.err.msg('Inconsistent indentation', lineno)
        if level == indentlevel + 1:
            indentlevel += 1
            tokens.append(Token('INDENT', '', lineno, 1 + tabsize * indentlevel))
        else:
            while indentlevel > level:
                indentlevel -= 1
                tokens.append(Token('DEDENT', '', lineno, 1 + tabsize * indentlevel))
        return indentlevel


    def match(self, text, nonterm):
        """ Look for match with nonterm at start of text.
            Return number of chars matched (-1 if no match).
        """
        if debug > 2:
            print 'match nonterm %s with "%s":' % (nonterm.name, text)
        for alt in nonterm.alternates:
            col = 0             # index to text
            skip = False
            for item in alt.items:
                if item.ischarclass() and item.text() == 'P':       # assumes P*
                    skip = True
                    continue            # on to next item
                length = self.match_item(text[col:], item, skip, alt)
                if length == -1:        # if item fails to match
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
        if text == '':
            return 0 if item.quantifier in '?*' else -1
        col = 0
        item_text = item.text()

        if skip:
            # last item was character class P*, so match any chars before this item
            if not item.isliteral():
                message = 'Terminal literal or EOL must follow character class P*'
                raise self.tokendef.err.msg(message, alt.linenum)
            col = text.find(item_text)
            if col == -1:       # item not found; but it may have zero occurrences, so
                col = 0         #   don't fail, just no progress (try next item)
            else:
                col += len(item_text)   # found it, move past it
            return col            
        
        # repeat item as quantifier allows
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
            if item.quantifier in '?*' or (item.quantifier == '+' and col > 0):
                # can do zero occurrences, so don't need to match
                length = max(0, length)     # 0 is worst case
            if item.quantifier not in '*+':   # can't repeat
                return length       # first time through, col == 0
            if length <= 0:
                return col
            col += length
            if item.separator and col < len(text):       
                # if item has separator, next char must be separator, or no repeat
                if text[col] == item.separator:
                    col += 1
                else:
                    return col
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
    ### To do: Check for mixed tabs and spaces, give error?
    for line in lines:
        if line.strip() == '':
            continue                        # skip blank line
        if line.startswith('\t'):
            return '\t'
        elif line.startswith(' '):
            numspaces = lcount(line, ' ')
            return ' ' * numspaces          # tab is some spaces
    return ' '      # if no indentation found

def lcount(line, chars):
    """ Count the number of consecutive characters in chars at beginning of line."""
    return len(line) - len(line.lstrip(chars))

    
## (Use a utility program to clean up indents in files?)
                

def reassemble(tokens):
    """ Return a string of tokens in lines similar to the original source."""
    level = 0
    result = ''
    lastkind = 'NEWLINE'
    for tkn in tokens:
        kind, string = tkn[0:2]
        if kind == 'NEWLINE':
            if lastkind == 'NEWLINE':
                result += '\n'
        elif kind == 'INDENT':
            level += 1
            continue
        elif kind == 'DEDENT':
            level -= 1
            continue
        else:
            if lastkind == 'NEWLINE':
                result += '\n' + ' ' * 4 * level
            if kind == 'COMMENT':
                if lastkind != 'NEWLINE':
                    result += ' \t\t'
                result += string
            elif kind in ('ASSIGN', 'RELATION') or kind.endswith('_OP'):
                result += ' ' + string + ' '
            else:
                if kind == 'NAME' and lastkind == 'KEYWORD':
                    result += ' '
                result += string
                result += ' ' * (string in ',')     # add a space after comma
        lastkind = kind
    return result



debug = 1

def test(source_filepath):
    global t

    language = source_filepath.rpartition('.')[-1]
    tokenspec = 'modspecs/%s.tokens' % language
    
    t = Tokenizer(tokenspec)
    print t.prefixes(),
    
    print 'prefix_map:'
    for prefix, kinds in sorted(t.tokendef.prefix_map.items()):
        kindnames = [kind.name for kind in kinds]
        print '%3s: %s' % (prefix, ' '.join(kindnames))
    print
        
    tokens = t.get_tokens(source_filepath)
    if debug == 1:
        print 'Tokens from ' + source_filepath + ':\n'
        for tkn in tokens:
            print tkn   
    ra = reassemble(tokens)
    print ra
    print


import sys

if __name__ == '__main__':

    if len(sys.argv) != 2:
        print 'Usage: %s <source_filepath>' % sys.argv[0]
    else:    
        source_filepath = sys.argv[1]
        test(source_filepath)

