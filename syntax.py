#!/usr/local/bin/python

# syntax.py
# Modsplan syntax parser
# Copyright 2011-2013 by David H Post, DaviWorks.com.


import sys

import grammar
import tokenize
import parsetree


class SyntaxGrammar(grammar.Grammar):
    """ Defines language syntax. """
    def __init__(self, filename):
        """ Load syntax grammar from file (format defined by metagrammar)."""
        grammar.Grammar.__init__(self, filename, SyntaxItem)
        if not self.root:
            raise self.err.msg('One nonterminal must be marked .root')
        # find prefixes for all nonterms and alternates
        for nonterm in self.nonterms.values():
            nonterm.find_prefixes(self.nonterms)


    def check_item(self, item, quantifier, alt):
        """ Check string item, with given quantifier, in alternate alt."""
        if item.isupper():          # tokenkind (terminal)
            pass
        else:
            item = grammar.Grammar.check_item(self, item, quantifier, alt)



class SyntaxItem(grammar.Item):
    """ Item extended for SyntaxGrammar."""
    
    def istokenkind(self):
        return self.element.isupper() and not self.isliteral()  # may have uppercase literals

    def isterminal(self):
        return self.isliteral() or self.istokenkind()


class SyntaxParser:
    """ Parse source code into syntax tree.
        Loads token and syntax grammars on initialization, to direct parsing.
    """
    def __init__(self, langname):
        """ Create parser by loading syntax grammar (langname.syntax) and 
            token grammar (langname.tokens).
            If grammars contain 'use' directives, import all needed files.
            To use multiple grammar files, create one file of 'use' directives.
        """
        self.tokenizer = tokenize.Tokenizer(langname + '.tokens')
        self.syntax = SyntaxGrammar(langname + '.syntax')
        self.source_filename = None
        self.err = None             # Error instance for reporting, set in parse()
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
        parse_tree = parsetree.new(nonterm.name)    # root of parse tree
        log(3, '\n\nParse trace:\n')
        if tokens:
            self.newtoken = True
            failure, numtokens = self.parse_nonterm(tokens, nonterm, parse_tree)
            print '\n\nParsed %d tokens of %d total.' % (numtokens, len(tokens))
            if numtokens < len(tokens):
                token = tokens[numtokens]
                self.syntax_error(token, failure)
        return parse_tree


    def syntax_error(self, token, expect=None):
        message = 'Syntax error at %s token "%s"' % (token.name, token.text)
        if expect:
            message += ': expecting %s' % expect
        raise self.err.msg(message, token)


    def parse_nonterm(self, tokens, nonterm, node):
        """ Parse tokens using syntax of nonterm; store parse tree in node. 
            Return parse item that failed (or None), number of tokens parsed.
            Report the failure that parsed the most tokens.
        """
        # Prefixes checked here
        numtokens = 0           # number of tokens matching syntax
        maxtokens = 0           # max number of tokens parsed among failed alternates
        token = tokens[0]
        if self.newtoken:
            log(3, token)           # display new token once
            self.newtoken = False
        if not self.inprefixes(token, nonterm.prefixes):
            failure = nonterm       # fail, nonterm not possible with this token
        else:
            # token must be in prefixes of some alternate
            for alt in nonterm.alternates:
                if self.inprefixes(token, alt.prefixes):    # this alternate may match
                    log(3, '%s => %s' % (nonterm, alt), node)
                    fail, numtokens = self.parse_alt(tokens, alt, node)
                    if fail:
                        if numtokens > maxtokens:
                            maxtokens = numtokens
                            failure = fail              # save maximum-token failure
                    else:
                        failure = None
                        log(4, '%s: %s' % (nonterm, listtokens(tokens[:numtokens])), node)
                        break       # success
        if failure:
            numtokens = maxtokens
            if isinstance(failure, grammar.Nonterminal):
                log(4, '%s failed: expected one of ' % nonterm, node)
                log(4, '    %s' % list(failure.prefixes), node)
            else:
                log(4, '%s failed: expected %s' % (nonterm, failure), node)
        log(5, 'numtokens = %d' % numtokens)
        return failure, numtokens


    @staticmethod
    def inprefixes(token, prefixes):
        """ Return true if token matches any of prefixes."""
        return token.text in prefixes or token.name in prefixes
        
    
    def parse_alt(self, tokens, alternate, node):
        """ Parse tokens using syntax of alternate; store parse tree in node. 
            Return parse item that failed (or None), number of tokens parsed.
            (Quantifiers handled here.)
        """
        numtokens = 0           # number of tokens matching syntax
        failure = None
        for item in alternate.items:
            failure, nt = self.parse_item(tokens[numtokens:], item, node)
            if failure:                     # wrong item
                if item.quantifier in '?*':     # zero repetitions allowed
                    failure = None                  # no failure, continue parsing alternate
                else:                           # item required, alternate fails
                    numtokens += nt                 # location of failure
                    node.remove_children()
                    break
            else:                           # one item parsed successfully
                numtokens += nt
                if item.quantifier in '+*':     # more than one repetition allowed
                    while numtokens < len(tokens):
                        failure, nt = self.parse_item(tokens[numtokens:], item, node)
                        if failure:                 # no more repetitions of item
                            failure = None              # not a failure, repetition optional
                            break
                        else:
                            numtokens += nt             # another item parsed successfully
        return failure, numtokens
    
    
    def parse_item(self, tokens, item, node):
        """ Parse tokens using syntax of item; store parse tree in node. 
            Return parse item that failed (or None), number of tokens parsed.
        """
        numtokens = 0           # number of tokens matching syntax
        token = tokens[0]
        if item.isterminal():
            # literal item matches token text; tokenkind matches token name
            match_text = token.text if item.isliteral() else token.name
            if match_text == item.text():
                numtokens = 1
                failure = None
                if token.text and not item.isliteral():
                    # don't output NEWLINE, INDENT, DEDENT, or literals
                    node.add_child(token.name, token.text)      # terminal node
                if self.newtoken:
                    log(3, token)           # if token display pending, show this one
                log(5, '    %s found' % item, node)
                self.newtoken = True    # show next token in trace
            else:
                log(5, '    %s not found' % item, node)
                failure = item      # item not found
        else:   # nonterminal
            nonterm = self.syntax.nonterms[item.text()]
            nonterm_node = node.add_child(nonterm.name)
            failure, numtokens = self.parse_nonterm(tokens, nonterm, nonterm_node)
            if failure:
                node.remove_child()
        return failure, numtokens

        
def listtokens(tokens):
    return ' '.join(map(str, tokens))


def log(msgtype, message, node=None):
    if str(msgtype) in debug:
        indent = node.indent() if node else ''
        print indent + str(message)


parser = None

def test(source_filename):
    global parser
    srcname, sep, langname = source_filename.rpartition('.')
    tree = None
    try:
        print '\n Parsing %s ... \n' % source_filename
        parser = SyntaxParser('grammars/' + langname)
        print 'Tokens loaded from ' + parser.tokenizer.tokendef.filename
        print 'Syntax loaded from ' + parser.syntax.filename
        if 's' in debug:
            parser.syntax.show()
        if 'p' in debug:
            print parser.syntax.show_prefixes()
        tree = parser.parse(source_filename)
        if 't' in debug:
            print '\n\nTree:\n'
            print tree.show()
        print "\n\n**** Syntax test done ****"
    except grammar.Error as exc:
        print exc
    print
    return tree


# debugging output selectors: 
#   o = tokens, p = prefixes, r = reassemble, s = syntax, t = tree, 
#   3, 4, 5 = parse trace levels
debug = 'or345t'  # default debugging output


if __name__ == '__main__':
    
    if len(sys.argv) in (2, 3):
        if len(sys.argv) == 3:
            debug = sys.argv[2]
        tree = test(sys.argv[1])
    else:
        print 'Usage: ./syntax.py <source_filename> [<debug_flags>]'

