#!/usr/local/bin/python

# tokenize.py
# Modsplan tokenizer
# Copyright 2011-2014 by David H Post, DaviWorks.com.

from __future__ import print_function       # for Python 2 compatibility

import grammar
from lineparsers import LineInfoParser, FileParser, Error


class Token:
    """ One symbol from source text; 
        for example: keyword, identifier, operator, punctuation, number."""
    
    def __init__(self, name, text, location, column, tabsize):
        self.name = name                    # name for the kind (the category) of the token
        self.text = text                    # string of chars from source
        self.location = location.copy()    
            # lineparsers.Location (filepath, linenum, column, etc)
        self.location.column = column       # column number of first char of token in source
        self.location.tabsize = tabsize     # used to expand tabs to display containing line
    
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
    
    def __init__(self, filepath):
        """ Load token grammar from file (format defined by tokens.metagrammar).
            Compute prefixes, and possible token kinds for each prefix.
        """
        grammar.Grammar.__init__(self, filepath, TokenItem)
        
        # nonterminals with uppercase names specify a kind of token
        # self.nonterms is an OrderedDict, so this preserves order of definition
        self.kinds = [nonterm for name, nonterm in self.nonterms.items() if name.isupper()]
        
        self.kindnames = [kind.name for kind in self.kinds]
        if 'newline' in self.options:
            self.kindnames += ['NEWLINE']
        if 'indent' in self.options:
            self.kindnames += ['INDENT', 'DEDENT']
        
        # Compute possible prefix character classes for each kind of token.
        #   prefix_map[char_class] is a list of kinds that can start with char_class.
        #   These lists preserve the order of tokenkinds in .tokens specification.
        self.prefix_map = dict()
        for kind in self.kinds:
            kind.find_prefixes(self.nonterms)       # stores prefixes in kind
            self._add_prefixes(kind)
            
    def _add_prefixes(self, tokenkind):
        """ Add prefixes of tokenkind to prefix_map."""
        # Compute list of possible token kinds for each prefix's character class
        for prefix in tokenkind.prefixes:
            # if prefix is already a character class (1 uppercase letter) just use it
            #       (needed for keywords and bool_ops)
            if TokenItem(prefix).ischarclass():
                chrclass = prefix
            else:
                chrclass = charclass(prefix[0])
            # Keep lists of tokenkinds ordered as in token grammar
            chrclass_kinds = self.prefix_map.setdefault(chrclass, [])   # new list if none
            if tokenkind not in chrclass_kinds:
                chrclass_kinds.append(tokenkind)
    
    def check_item(self, item, quantifier, alt):
        """ Check string item, with given quantifier, in alternate alt."""
        if item.isupper() and len(item) == 1:       # check for valid character class
            if item not in ('L', 'U', 'D', 'P'):
                raise alt.location.error('Unrecognized character class (%s)' % item)
            elif item == 'P' and quantifier != '*':
                raise alt.location.error('Character class P must be used with *, error')
        else:
            grammar.Grammar.check_item(self, item, quantifier, alt)


class TokenItem(grammar.Item):
    """ One item of a production: character class, literal, or nonterm."""
            
    def ischarclass(self):
        """ Is item a character class specifier (one uppercase letter)?"""
        return len(self.element) == 1 and self.element.isupper()

    def isterminal(self):
        return self.isliteral() or self.ischarclass()
        

class Tokenizer:
    """ Configurable tokenizer. Reads a token specification grammar,
        then parses source text into tokens, as defined by the grammar.
    """
    def __init__(self, grammar_filename):
        """ Create tokenizer from grammar file (format defined in tokens.metagrammar).
            The grammar defines the syntax and kinds of tokens.
            If grammar contains 'use' directives, import all needed files.
            To use multiple grammar files, create one file of 'use' directives.
            Grammar commands may enable emitting of NEWLINE, INDENT & DEDENT tokens.
        """
        self.tokendef = TokenGrammar(grammar_filename)  # load token definitions
        self.sourcepath = None          # set in get_tokens()


    def prefixes(self):
        """ Return text table of prefixes for each token kind."""
        text = '\nPrefixes for token kinds:\n'
        for kind in self.tokendef.kinds:
            text += '%s: %s\n' % (kind.name, sorted(kind.prefixes))
        return text + '\n'


    def get_tokens(self, sourcepath, tabsize=4, enable_imports=False):
        """ Tokenize source from sourcepath, return a list of Token.
            tabsize is # of spaces per tab char, to report accurate column #s.
            If imports enabled, source may import other source files.
        """
        self.sourcepath = sourcepath
        enable_newline = 'newline' in self.tokendef.options
        enable_indent = 'indent' in self.tokendef.options
        lineparser = LineInfoParser if enable_imports else FileParser
        lines = lineparser(sourcepath, track_indent=enable_indent)
        
        # Read lines from source, tokenize
        tokens = []
        indentlevel = 0
        
        for line in lines:
            loc = lines.location
            tokens += self.indents(loc.level - indentlevel, loc, tabsize)
            indentlevel = loc.level
            col = 0             # column of line
            viewcol = 1         # column as viewed in source (1-origin, expand tabs)
            
            while col < len(line):
                char = line[col]
                chclass = charclass(char)
                
                # find longest match among tokenkinds that can begin with this char class
                kinds = self.tokendef.prefix_map.get(chclass, [])   # empty list if none
                maxlength = 0           # length of longest token matched
                kindname = ''           # remember kind of longest token
                for kind in kinds:
                    length = self.match_nonterm(line[col:], kind)
                    if length > maxlength:
                        maxlength = length
                        kindname = kind.name
                        
                if maxlength > 0:       # match found
                    text = line[col:col + maxlength]
                    tokens.append(Token(kindname, text, loc, viewcol, tabsize))
                    col += maxlength
                    viewcol += maxlength
                        
                else:  # no match found for any kind starting with char
                    if not char.isspace():          # skip whitespace
                        tokens.append(Token('', char, loc, viewcol, tabsize))  # punctuation
                    col += 1
                    viewcol += tabsize if char == '\t' else 1
                    
            if enable_newline:
                tokens.append(Token('NEWLINE', '', loc, viewcol, tabsize))     # end of line

        # close indented blocks
        tokens += self.indents(- indentlevel, loc, tabsize)
        return tokens


    def indents(self, change, location, tabsize):
        """ Return list of indent or dedent tokens, for change in indent level."""
        # ignores multiple-level indents (usually a continuation of prev line)
        if change == 1:
            return [Token('INDENT', '', location, 1, tabsize)]
        else:
            return (- change) * [Token('DEDENT', '', location, 1, tabsize)]


    def match_nonterm(self, text, nonterm):
        """ Look for match with nonterm at start of text.
            Return number of chars matched (-1 if no match).
        """
        if '2' in debug:
            print('match nonterm %s with "%s":' % (nonterm.name, text))
        maxchars = -1       # length of longest token that matched
        for alt in nonterm.alternates:
            col = 0             # index to text
            skip = False
            
            for item in alt.items:
                if item.ischarclass() and item.text() == 'P':       # assumes P*
                    skip = True
                    continue            # on to next item
                length = self.match_item(text[col:], item, skip)
                if '2' in debug:
                    print('   %d chars of "%s" matched %s' % (length, text[col:], item))
                if length == -1:        # if item fails to match
                    break                   # try next alternate
                skip &= (length == 0)   # stop skip if literal found
                col += length
            else:               # end of alt, it matched
                if skip:            # P* was last item in alternate,
                    col = len(text)     # so it matches the rest of the text
                maxchars = max(col, maxchars)   # remember longest of alternates
        return maxchars


    def match_item(self, text, item, skip):
        """ Look for match with item at start of text, return # of chars matched,
            or -1 if no match. If skip, skip chars until item is found.
        """
        if text == '':
            return (0 if item.quantifier in '?*' else -1)
        item_text = item.text()

        if skip:
            # last item was character class P*, so match any chars before current item
            #   (current item must be a literal, checked when grammar loaded)
            column = text.find(item_text)
            if column == -1:
                return column                       # not found
            else:
                return column + len(item_text)      # found it, move past it
            
        length = self.match_single(text, item)
        if length == -1:        # not a match
            if item.quantifier in '?*':
                length = 0          # zero occurrences OK, report a zero length match
            return length
        
        # we have a match
        if item.quantifier not in '*+':     # no repeat allowed
            return length
        if length == 0:                     # zero length match, can't repeat
            return length
        column = length

        # repeat item as quantifier allows
        while column < len(text):
            length = self.match_single(text[column:], item)
            if length <= 0:
                return column       # done, no more repeats
            column += length
            
            if item.separator and column < len(text):       
                # if item has separator, next char must be separator, or no repeat
                if text[column] == item.separator:
                    column += 1
                else:
                    return column   # no separator, done
        return column
    
    
    def match_single(self, text, item):
        """ Match text with single occurence of item, 
            return number of chars matched or -1 if no match."""
        length = -1         # failure unless otherwise determined
        item_text = item.text()
        if item.ischarclass():
            if item_text == charclass(text[0]):
                length = 1
        elif item.isliteral():
            if text.startswith(item_text):
                length = len(item_text)
        else:   # item must be a nonterminal
            nonterm = self.tokendef.nonterms[item_text]
            length = self.match_nonterm(text, nonterm)
        if '3' in debug:
            print('      %d chars of "%s" match %s' % (length, text, item))
        return length
    

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
                

def reassemble(tokens):
    """ Return a string of tokens in lines similar to the original source."""
    ### Works only for languages using NEWLINE tokens
    level = 0
    result = ''
    lastkind = 'NEWLINE'
    
    for token in tokens:
        kind = token.name
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
                result += token.text
            elif kind in ('ASSIGN', 'RELATION') or kind.endswith('_OP'):
                result += ' ' + token.text + ' '
            else:
                if token.text[0].isalnum() and result[-1:].isalnum():
                    result += ' '
                result += token.text
                if token.text == ',':
                    result += ' '
        lastkind = kind
    return result + '\n'


debug = ''

def test(source_filepath):
    global t
    try:
        language = source_filepath.rpartition('.')[-1]
        tokenspec = 'modspecs/%s.tokens' % language
        
        t = Tokenizer(tokenspec)
        print(t.prefixes())
        
        print('prefix_map:')
        for prefix, kinds in sorted(t.tokendef.prefix_map.items()):
            kindnames = [kind.name for kind in kinds]
            print('%3s: %s' % (prefix, ' '.join(kindnames)))
        print()
            
        tokens = t.get_tokens(source_filepath)
        if 'o' in debug:
            print('Tokens from ' + source_filepath + ':\n')
            for tkn in tokens:
                print(tkn)   
        
        print(reassemble(tokens))

    except (None if 'b' in debug else Error) as exc:
        print(exc)


import sys

if __name__ == '__main__':
    args = sys.argv[1:] + ['']
    if len(args) in (2, 3):
        source_filepath, debug = args[:2]
        test(source_filepath)
    else:    
        print("""
    Usage: %s <source_path> [-<debug_flags>]
        
        debug_flags (may be combined, as in -2ob):

        2 = log nonterm matching to stdout
        3 = log item matching to stdout
        b = show traceback on error
        o = list tokens from source file
        """ % sys.argv[0])
