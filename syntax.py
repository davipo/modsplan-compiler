# Modsplan syntax parser
# author: David Post
# date: 2011-05-27


import grammar
import tokenize



class SyntaxGrammar(grammar.Grammar):
    """ Defines language syntax. """
    def __init__(self, filename):
        """ Load syntax grammar from file (format defined by metagrammar)."""
        grammar.Grammar.__init__(self, filename, SyntaxItem)
        if not self.root:
            self.err.msg('One nonterminal must be marked .root')
        # find prefixes for all nonterms and alternates
        for nonterm in self.nonterms.values():
            nonterm.find_prefixes(self.nonterms)


class SyntaxItem(grammar.Item):
    """ Item extended for SyntaxGrammar."""
    
    def istokenkind(self):
        return self.element.isupper() and not self.isliteral()  # may have uppercase literals

    def isterminal(self):
        return self.isliteral() or self.istokenkind()



class ParseNode:
    """ A node of the parse tree. """
    def __init__(self, name, content=None, level=0):
        self.name = name                # name of nonterminal or terminal
        self.level = level              # depth of node in tree
        if isinstance(content, str):
            self.content = content      # terminal text
        else:
            self.content = list()       # new list of child nodes ([] would be reused)

    def __str__(self):
        if self.isterminal():
            return self.name + '(' + self.content + ')'
        else:       # must be list (guaranteed by __init__)
            # check that all items in list are ParseNode?
            return self.name + '[' + ', '.join([str(child) for child in self.content]) + ']'

    def isterminal(self):
        return isinstance(self.content, str)

    def add_child(self, child):
        """ Append child node to this node's list of children. """
        if isinstance(self.content, list):
            self.content.append(child)
            child.level = self.level + 1
        else:
            grammar.Error().msg('Cannot add child (%s) to terminal node (%s)' %
                                (child, self))

    def remove_children(self):
        self.content = list()
    
#     def has_children(self):
#         return not self.isterminal() and len(self.content) > 0
    
    def show(self, indent='   ', level=0):
        """ Return display (as string) of parse tree starting at this node.
            level is indent level; indent string contains one indent (tab or spaces).
        """
        result = ''
        if self.isterminal():
            result += level * indent + str(self) + '\n'
        else:
            result += level * indent + self.name + '\n'
            for node in self.content:
                result += node.show(indent, level + 1)
        return result
        
    def indent(self, extra=0):
        return '    ' * (self.level + extra)
        

class SyntaxParser:
    """ Parse source code into syntax tree.
        Loads token and syntax grammars on initialization, to direct parsing.
    """
    def __init__(self, filename):
        """ Create parser by loading syntax grammar (filename.syntax) and 
            token grammar (filename.tokens).
            If grammars contain 'use' directives, import all needed files.
            To use multiple grammar files, create one file of 'use' directives.
        """
        self.tokenizer = tokenize.Tokenizer(filename + '.tokens')
        self.syntax = SyntaxGrammar(filename + '.syntax')
        self.source_filename = None
        self.err = None             # Error instance for reporting, set in parse()
        self.expected = None        # when parse fails, expected item or nonterm, else None
        self.newtoken = False       # True when new token will be parsed (for trace display)

        
    def parse(self, filename):
        """ Parse given source file, return root node of parse tree.
            Syntax error will raise Exception.
        """
        self.source_filename = filename
        self.err =  tokenize.Error(filename)
        tokens = self.tokenizer.token_generator(filename)
        tokens = list(tokens)
        if 'o' in debug:
            print '\nTokens from ' + filename + ':\n'
            for tkn in tokens:
                print tkn
            print
        if 'r' in debug:
            print '\nReassembled source from tokens:'
            print tokenize.reassemble(tokens)
            
        # Start at syntax root, find terminals matching tokens of source file.
        # Build parse tree depth-first, climbing syntax to classify nodes.
        nonterm = self.syntax.root
        parse_tree = ParseNode(nonterm.name)        # root of parse tree
        log(3, '\nParse trace:\n')
        if tokens:
            self.newtoken = tokens[0]
            numtokens = self.parse_nonterm(tokens, nonterm, parse_tree)
            print '\n\nParsed %d tokens of %d total.' % (numtokens, len(tokens))
            if numtokens < len(tokens):
                token = tokens[numtokens]
                self.syntax_error(token, self.expected)
        return parse_tree


    def syntax_error(self, token, expect=None):
        message = 'Syntax error at %s token "%s"' % (token.name, token.text)
        if expect:
            message += ': expecting %s' % expect
        self.err.msg(message, token)


    def parse_nonterm(self, tokens, nonterm, node):
        """ Parse tokens using syntax of nonterm; store parse tree in node. 
            Return number of tokens parsed successfully.
            If parse fails, set self.expected to grammar item not found.
            Reported failure is that of the last viable alternate; we could
            report the failure that parsed the most tokens successfully.
        """
        # Prefixes checked here
        numtokens = 0           # number of tokens matching syntax
        token = tokens[0]
        if not self.inprefixes(token, nonterm.prefixes):
            self.expected = nonterm     # fail, nonterm not possible with token
        else:
            # token must be in prefixes of some alternate
            for alt in nonterm.alternates:
                if self.inprefixes(token, alt.prefixes):    # this alternate may match
                    if self.newtoken:
                        log(3, token)           # display new token once
                        self.newtoken = False
                    log(3, '%s => %s' % (nonterm, alt), node)
                    self.expected = None        # forget previous failures
                    numtokens = self.parse_alt(tokens, alt, node)
                    if not self.expected:
                        log(4, '%s: %s' % (nonterm, listtokens(tokens[:numtokens])), node)
                        break       # success
        if self.expected:
            if isinstance(self.expected, grammar.Nonterminal):
                log(4, '%s failed: expected one of ' % nonterm, node)
                log(4, '    %s' % list(self.expected.prefixes), node)
            else:
                log(4, '%s failed: expected %s' % (nonterm, self.expected), node)
        return numtokens


    @staticmethod
    def inprefixes(token, prefixes):
        """ Return true if token matches any of prefixes."""
        return token.text in prefixes or token.name in prefixes
        
    
    def parse_alt(self, tokens, alternate, node):
        """ Parse tokens using syntax of alternate; store parse tree in node. 
            Return number of tokens parsed. Quantifiers handled here.
        """
        numtokens = 0           # number of tokens matching syntax
        for item in alternate.items:
            nt = self.parse_item(tokens[numtokens:], item, node)
            if self.expected:               # wrong item
                if item.quantifier in '?*':     # zero repetitions allowed
                    self.expected = None            # no failure, continue parsing alt
                else:                           # item cannot be missing, alt fails
                    numtokens += nt                 # location of failure
                    node.remove_children()
                    break
            else:                           # one item parsed successfully
                numtokens += nt
                if item.quantifier in '+*':     # more than one repetition allowed
                    while numtokens < len(tokens):
                        nt = self.parse_item(tokens[numtokens:], item, node)
                        if self.expected:           # failed, no more repetitions of item
                            self.expected = None        # cancel failure, repetition optional
                            break
                        else:
                            numtokens += nt             # another item parsed successfully
        return numtokens
    
    
    def parse_item(self, tokens, item, node):
        """ Parse tokens using syntax of item; store parse tree in node. 
            Return number of tokens parsed.
        """
        numtokens = 0           # number of tokens matching syntax
        token = tokens[0]
        if item.isterminal():
            if item.isliteral():
                if token.text == item.text():
                    numtokens = 1
            else:  # must be tokenkind
                if token.name == item.text() :
                    numtokens = 1
                    if token.text:          # don't output NEWLINE, INDENT, DEDENT
                        node.add_child(ParseNode(token.name, token.text))
            if numtokens == 1:
                log(5, '    %s found' % item, node)
            else:
                log(5, '    %s not found' % item, node)
                self.expected = item    # item not found
            self.newtoken = numtokens == 1      # show new token in trace
        else:   # nonterminal
            nonterm = self.syntax.nonterms[item.text()]
            nonterm_node = ParseNode(nonterm.name, level=node.level + 1)
            numtokens = self.parse_nonterm(tokens, nonterm, nonterm_node)
            if not self.expected:       # success
                node.add_child(nonterm_node)
        return numtokens
        
        
def listtokens(tokens):
    return ' '.join(map(str, tokens))


def log(msgtype, message, node=None):
    if str(msgtype) in debug:
        indent = node.indent() if node else ''
        print indent + str(message)


#### use in pdb with alias v scalars(locals()) ?
def scalars(d):
    """ Print strings and non-container items in dict d. """
    for k, v in d.items():
        if isinstance(v, str) or not hasattr(v, '__len__'):     # no length, not a sequence
            print k + ' = ' + str(v)


parser = None

def test(source, grammar):
    global parser
    parser = SyntaxParser('grammars/' + grammar)
    print 'Syntax loaded from ' + parser.syntax.filename
    if 's' in debug:
        parser.syntax.show()
    if 'p' in debug:
        print parser.syntax.show_prefixes()
    tree = parser.parse(source)
    if 't' in debug:
        print '\n\nTree:\n'
        print tree.show()
    print "\n\n**** Syntax test done ****"
    return tree


# debug: o = tokens, p = prefixes, r = reassemble, s = syntax, t = tree, 
#        3, 4, 5 = parse trace levels
debug = 'or345t'


if __name__ == '__main__':
    src = 'sample.lang'
    src = 'snape.lang'
#     src = 'snop.lang'
    src = 'sample source/' + src
#     tree = test(src, 'L0')

    src = 'grammars/small.defn'
#     src = 'grammars/smaller.defn'
#     src = 'grammars/assign.defn'
    tree = test(src, 'defn')
    

