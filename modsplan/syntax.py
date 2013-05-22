#!/usr/local/bin/python

# syntax.py
# Modsplan syntax parser
# Copyright 2011-2013 by David H Post, DaviWorks.com.


import sys
import os.path

import grammar
import tokenize
import parsetree

Error = grammar.Error


class SyntaxGrammar(grammar.Grammar):
    """ Defines language syntax. """
    
    def __init__(self, filepath, tokenkindnames):
        """ Load syntax grammar from file (format defined by metagrammar);
            check for valid tokenkindnames."""
        self.tokenkindnames = tokenkindnames
        grammar.Grammar.__init__(self, filepath)
        if not self.root:
            raise Error('One nonterminal must be marked .root', self)
        # find prefixes for all nonterms and alternates
        for nonterm in self.nonterms.values():
            nonterm.find_prefixes(self.nonterms)

    def check_item(self, item, quantifier, alt):
        """ Check string item, with given quantifier, in alternate alt."""
        if item.isupper() and item not in self.tokenkindnames:
            raise Error('Unrecognized tokenkind (%s)' % item, alt)
        else:
            grammar.Grammar.check_item(self, item, quantifier, alt)


class SyntaxParser:
    """ Parse source code into syntax tree.
        Loads token and syntax grammars on initialization, to direct parsing.
    """
    def __init__(self, langpath, debug=''):
        """ Create parser by loading syntax grammar (langpath.syntax) and 
            token grammar (langpath.tokens).
            If grammars contain 'use' directives, import all needed files.
            To use multiple grammar files, create one file of 'use' directives.
            Optional debugging flags.
        """
        self.debug = debug          # debugging flags
        
        self.tokenizer = tokenize.Tokenizer(langpath + '.tokens')
        if '2' in self.debug:
            print 'Token spec loaded from ' + self.tokenizer.tokendef.filepath
            
        self.syntax = SyntaxGrammar(langpath + '.syntax', self.tokenizer.tokendef.kindnames)
        if '2' in self.debug:
            print 'Syntax spec loaded from ' + self.syntax.filepath
            
        if 's' in self.debug:
            self.syntax.show()
        if 'p' in self.debug:
            print self.syntax.show_prefixes()
            
        self.source_path = ''       # last source file parsed
        self.maxtokens = 0          # greatest number of tokens parsed before a parse failure
        self.expected = None        # grammar item expected at furthest failure
        self.tokens = None          # list of tokens in source file
        self.newtoken = False       # True when new token will be parsed (for trace display)

        
    def parse(self, filepath, enable_imports=False):
        """ Parse given source file, return root node of parse tree.
            Syntax error will raise Error exception.
            If imports enabled, source may import other source files.
        """
        self.source_path = filepath
        self.tokens = self.tokenizer.get_tokens(filepath, enable_imports=enable_imports)
        
        if 'o' in self.debug:
            print '\nTokens from ' + filepath + ':\n'
            for tkn in self.tokens:
                print tkn
            print
        if 'r' in self.debug:
            print '\nReassembled source from tokens:'
            print tokenize.reassemble(self.tokens)
            
        # Start at syntax root, find terminals matching tokens of source file.
        # Build parse tree depth-first, climbing syntax to classify nodes.
        nonterm = self.syntax.root
        parse_tree = parsetree.new(nonterm.name, self.debug)    # root of parse tree
        self.log(3, '\n\nParse trace:\n')
        if self.tokens:
            numtokens = self.parse_comments(0, parse_tree)
            self.newtoken = True
            failure, nt = self.parse_nonterm(numtokens, nonterm, parse_tree)
            numtokens += nt
            
            if failure or numtokens < len(self.tokens):     # end not reached
                self.syntax_error(numtokens)
            elif '1' in self.debug:
                print '\n%s parsed successfully (%d tokens)' % (filepath, numtokens)
                
        if 't' in self.debug:
            print '\nTree:\n'
            print parse_tree.show()
        return parse_tree


    def syntax_error(self, numtokens):
        """ Raise Error with appropriate message for. """
        message = '\nParsed %d tokens of %d total for %s'
        print message % (numtokens, len(self.tokens), self.source_path)
        if self.maxtokens < len(self.tokens):
           token = self.tokens[self.maxtokens]
           message = 'Syntax error at %s token "%s"' % (token.name, token.text)
           column = token.column
        else:
           token = self.tokens[self.maxtokens - 1]
           message = 'Syntax error at end of file'
           column = 1 + len(token.line())
        message += ': expecting %s' % self.expected
        raise Error(message, token)
    

    def parse_comments(self, start, node):
        """ Parse comments from self.tokens beginning at index start, add them to node;
            return number of comment tokens."""
        numtokens = 0
        for token in self.tokens[start:]:
            if token.name == 'COMMENT':
                node.add_child(token)
                self.log(5, 'COMMENT from line %d: %s' % (token.linenum, token.text))
                numtokens += 1
            else:
                break
        return numtokens
        

    def parse_nonterm(self, start, nonterm, node):
        """ Parse tokens from index start using syntax of nonterm;
                if successful, store parse tree in node. 
            Return parse item that failed (or None), number of tokens parsed.
            If success, keep parse that parses the most tokens (first if tied);
                if failure, return failure that parses the most tokens (first if tied).
        """
        maxtokens = 0           # max number of tokens parsed among alternates
        token = self.tokens[start]
        node.set_location(token)
        if self.newtoken:
            self.log(3, token)      # display new token once
            self.newtoken = False
        
        if self.inprefixes(token, nonterm.prefixes):
            # token must be in prefixes of some alternate
            numchildren = 0     # number of children parsed from longest successful alternate
            failure = 'not set'     # replace with failed item, or None
            
            # Parse all alternates, retain longest (successful, if any) parse
            for alt in nonterm.alternates:
                if self.inprefixes(token, alt.prefixes):    # this alternate may match
                    self.log(3, '%s => %s' % (nonterm, alt), node)
                    fail, numtokens = self.parse_alt(start, alt, node)
                    if not fail:
                        tokens = self.tokens[start:][:numtokens]
                        self.log(4, '%s: %s' % (nonterm, listtokens(tokens)), node)
                        if numtokens == maxtokens and not failure and 'a' not in self.debug:
                            # a second alternate matches the same tokens
                            raise Error('Ambiguous parse of %s' % nonterm, tokens[-1])
                        
                    if failure or not fail:     # status same or better than previous best
                        first_alt = (failure == 'not set')          # first alternate
                        first_success = failure and not fail
                        if numtokens > maxtokens or first_success or first_alt:
                            maxtokens = numtokens
                            failure = fail              # save result
                            if not fail:                # remove previous alt's parse
                                node.remove_children(numchildren)
                                numchildren = node.numchildren()
                    
                    if node.numchildren() > numchildren:    # if this parse was not best,
                        node.keep_children(numchildren)     #   discard it and keep previous
        
        else:   # fail, nonterm not possible with this token
            failure = nonterm
        
        if failure:
            if start + maxtokens > self.maxtokens:
                self.maxtokens = start + maxtokens      # record furthest failure
                self.expected = failure
            if isinstance(failure, grammar.Nonterminal):
                self.log(4, '%s failed: expected one of ' % nonterm, node)
                self.log(4, '    %s' % list(failure.prefixes), node)
            else:
                self.log(4, '%s failed: expected %s' % (nonterm, failure), node)
        return failure, maxtokens


    @staticmethod
    def inprefixes(token, prefixes):
        """ Return true if token matches any of prefixes."""
        return token.text in prefixes or token.name in prefixes
        
    
    def parse_alt(self, start, alternate, node):
        """ Parse tokens from index start using syntax of alternate; store parse tree in node. 
            Return parse item that failed (or None), number of tokens parsed.
            (Quantifiers handled here.)
        """
        numtokens = 0           # number of tokens matching syntax
        failure = None
        for item in alternate.items:
            
            if item.quantifier == '1':      # no quantifier
                failure, nt = self.parse_item(start + numtokens, item, node)
                numtokens += nt
            
            else:       # quantified item: make cover node, occurrences are children of it
                qnode = node.add_child(item.strq())     # name is item followed by quantifier
                failure, nt = self.parse_item(start + numtokens, item, qnode)

                if failure:     # wrong item
                    if item.quantifier in '?*':     # zero repetitions allowed
                        failure = None                  # no fail, continue parsing alternate
                    else:                           # item required, alternate fails
                        numtokens += nt                 # location of failure
                
                else:           # one item parsed successfully
                    numtokens += nt
                    if item.quantifier in '+*':
                    
                        # more than one repetition allowed, try parsing more
                        while start + numtokens < len(self.tokens):
                        
                            if item.separator:
                                token = self.tokens[start + numtokens]
                                if token.text == item.separator:
                                    numtokens += 1
                                else:
                                    break       # no separator, no repeat

                            failure, nt = self.parse_item(start + numtokens, item, qnode)
                            if failure:                 # no more repetitions of item
                                failure = None              # OK, repetition optional
                                break
                            else:
                                numtokens += nt             # another item parsed successfully
            
            if failure:     # wrong item, alternate fails
                break
        return failure, numtokens
    
    
    def parse_item(self, start, item, node):
        """ Parse tokens from index start using syntax of item; store parse tree in node. 
            Return parse item that failed (or None), number of tokens parsed.
        """
        numtokens = 0           # number of tokens matching syntax
        if start == len(self.tokens):
            return item, numtokens          # fail: no tokens left
        token = self.tokens[start]
        node.set_location(token)
        
        if item.isterminal():
            # literal item matches token text; tokenkind matches token name
            match_text = token.text if item.isliteral() else token.name
            if match_text == item.text():
                numtokens = 1
                failure = None
                if token.text and not item.isliteral():
                    # don't output NEWLINE, INDENT, DEDENT, or literals
                    node.add_child(token)   # terminal node
                if self.newtoken:
                    self.log(3, token)      # if token display pending, show this one
                self.log(5, '    %s found' % item, node)
                self.newtoken = True    # show next token in trace
                numtokens += self.parse_comments(start + numtokens, node)
            else:
                self.log(5, '    %s not found' % item, node)
                failure = item      # item not found
            
        else:   # nonterminal
            nonterm = self.syntax.nonterms[item.text()]
            nonterm_node = node.add_child(nonterm.name)
            failure, numtokens = self.parse_nonterm(start, nonterm, nonterm_node)
            if failure:
                node.remove_child()
        return failure, numtokens


    def log(self, msgtype, message, node=None):
        if str(msgtype) in self.debug:
            indent = node.indent() if node else ''
            print indent + str(message)

        
def listtokens(tokens):
    return ' '.join(map(str, tokens))


parser = None

def test(source_filepath, grammar_dir=None, debug=''):
    global parser
    if grammar_dir == None:
        grammar_dir = 'modspecs/'
    srcname, sep, langname = source_filepath.rpartition('.')
    tree = None
    try:
        print '\nParsing %s ... \n' % source_filepath
        parser = SyntaxParser(os.path.join(grammar_dir, langname), debug)
        tree = parser.parse(source_filepath, enable_imports=('i' in debug))
        print "\n**** Syntax test done ****"
    except Error as exc:
        print exc
    print
    return tree


# debugging output selectors: 
#   o = tokens, p = prefixes, r = reassemble, s = syntax, t = tree, i = enable imports
#   3, 4, 5 = parse trace levels

if __name__ == '__main__':
    debug = 't'     # default debugging output
    
    if 2 <= len(sys.argv) <= 4:
        sourcepath = sys.argv[1]
        grammar_dir = None              # use default if None
        for arg in sys.argv[2:]:
            if arg.startswith('-'):
                debug = arg[1:]
            else:
                grammar_dir = arg
        tree = test(sourcepath, grammar_dir, debug)
    else:
        print 'Usage: ./syntax.py <source_filepath> [<grammar_dir>] [-<debug_flags>]'

