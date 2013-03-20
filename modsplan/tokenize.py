# tokenize.py
# Modsplan tokenizer
# Copyright 2011-2013 by David H Post, DaviWorks.com.


import grammar
import lineparsers

Error = lineparsers.Error


class Token:
    """ One symbol from source text; 
        for example: keyword, identifier, operator, punctuation, number."""
    
    def __init__(self, name, text, info, column, tabsize):
        self.name = name                    # name for the kind (the category) of the token
        self.text = text                    # string of chars from source
        self.linenum = info.linenum         # line number where found in source (1-origin)
        self.filepath = info.filepath       # source file
        self.lines = info.info.lines        # list of source lines
        self.column = column                # column number of first char of token in source
        self.tabsize = tabsize              # used to expand tabs to display containing line
    
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

    def line(self):
        """ Return line of source file containing this token, with tabs expanded."""
        return self.lines[self.linenum - 1].replace('\t', ' ' * self.tabsize)


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
            kind.prefixes.discard(None)   ## should not have None, but in case (give error?)
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
                raise Error('Unrecognized character class (%s)' % item, alt)
            elif item == 'P' and quantifier != '*':
                raise Error('Character class P must be used with *, error', alt)
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
        self.tabsize = 0                # for reporting column number, set in get_tokens()
        self.sourcepath = None          # set in get_tokens()


    def prefixes(self):
        """ Return text table of prefixes for each token kind."""
        text = '\nPrefixes for token kinds:\n'
        for kind in self.tokendef.kinds:
            text += '%s: %s\n' % (kind.name, list(kind.prefixes))
        return text + '\n'


    def get_tokens(self, sourcepath, tabsize=4, enable_imports=False):
        """ Tokenize source from sourcepath, return a list of Token.
            tabsize is # of spaces per tab char, to report accurate column #s.
            If imports enabled, source may import other source files.
        """
        self.sourcepath = sourcepath
        self.tabsize = tabsize              # for reporting column number in errors
        enable_newline = 'newline' in self.tokendef.options
        enable_indent = 'indent' in self.tokendef.options
        lineparser = lineparsers.LineInfoParser if enable_imports else lineparsers.FileParser
        lines = lineparser(sourcepath, track_indent=enable_indent)
        
        # Read lines from source, tokenize
        tokens = []
        indentlevel = 0
        
        for line in lines:
            tokens += self.indents(lines.level - indentlevel, lines)
            indentlevel = lines.level
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
                    tokens.append(Token(kindname, text, lines, viewcol, tabsize))
                    col += maxlength
                    viewcol += maxlength
                        
                else:  # no match found for any kind starting with char
                    if not char.isspace():          # skip whitespace
                        tokens.append(Token('', char, lines, viewcol, tabsize))  # punctuation
                    col += 1
                    viewcol += tabsize if char == '\t' else 1
                    
            if enable_newline:
                tokens.append(Token('NEWLINE', '', lines, viewcol, tabsize))   # end of line

        # close indented blocks
        tokens += self.indents(- indentlevel, lines)
        return tokens


    def indents(self, change, line_info):
        """ Return list of indent or dedent tokens, for change in indent level."""
        # ignores multiple-level indents (usually a continuation of prev line)
        if change == 1:
            return [Token('INDENT', '', line_info, 1, self.tabsize)]
        else:
            return (- change) * [Token('DEDENT', '', line_info, 1, self.tabsize)]


    def match_nonterm(self, text, nonterm):
        """ Look for match with nonterm at start of text.
            Return number of chars matched (-1 if no match).
        """
        if debug > 2:
            print 'match nonterm %s with "%s":' % (nonterm.name, text)
        maxchars = -1       # length of longest token that matched
        for alt in nonterm.alternates:
            col = 0             # index to text
            skip = False
            
            for item in alt.items:
                if item.ischarclass() and item.text() == 'P':       # assumes P*
                    skip = True
                    continue            # on to next item
                length = self.match_item(text[col:], item, skip)
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
            or -1 if no match. If skip, skip chars until item is found, or end.
        """
        if debug > 2:
            print '   match_item %s with "%s"' % (item, text)
        if text == '':
            return (0 if item.quantifier in '?*' else -1)
        col = 0
        item_text = item.text()

        if skip:
            # last item was character class P*, so match any chars before current item
            #   (current item must be a literal, checked when grammar loaded)
            col = text.find(item_text)
            if col == -1:       # item not found; but it may have zero occurrences, so
                col = 0         #   don't fail, just no progress (try next item)
            else:
                return col + len(item_text)     # found it, move past it
        
        # repeat item as quantifier allows
        while col < len(text):
            length = self.match_single(text[col:], item)
                # we have a match unless length == -1
                
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
                

nametokens = ('NAME', 'KEYWORD', 'ATTRIBUTE')

def reassemble(tokens):
    """ Return a string of tokens in lines similar to the original source."""
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
                if kind in nametokens and lastkind in nametokens:
                    result += ' '
                result += token.text
                result += ' ' * (token.text in ',')     # add a space after comma
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

