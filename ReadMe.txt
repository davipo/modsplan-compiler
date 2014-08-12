modsplan-compiler/ReadMe.txt
ModSPLan - Modular Specification of Programming Languages
Modsplan implements a universal compiler, driven by language specifications.

Please read the introduction to this project at modsplan.com


Version 0.2.8 of the Modsplan compiler is 1932 lines of pure Python, 
plus 84 lines of specifications used internally. It uses no external libraries.

Modsplan requires Python 2.7
Run "python modsplan/compiler.py" on your command line for usage information.


A simple calculator example:
  (Compare with Lex & Yacc example at http://pltplp.net/lex-yacc/example.html)
  (See modspecs/calc.* for specifications)

    $ cat sample_source/example.calc
    4 + 2 * -1.5

    $ python modsplan/compiler.py sample_source/example.calc

    sample_source/example.calc parsed successfully (6 tokens)

    const 4
    const 2
    const 0
    const 1.5
    sub
    mul
    add


Files:

ReadMe.txt          This file

License.txt         License terms

sample_source/      Source code examples for testing compiler
                        *.sbil files are generated SBIL code

modspecs/           Modsplan specification files (.tokens, .syntax, .defn)
    
    *.metagrammar specify the syntax of Modsplan specification files
    
    calc is a simple calculator example
        See sample_source/example.calc and example.calc.sbil generated code
    
    L0 is a small statically-typed language with Python-like syntax
    c1 is a working subset of C
    base, expr, constants, float: specs shared between languages
    
    sbil is Stack-Based Intermediate Language (based on LLVM), our target code
    llvm is an attempt to specify the syntax of LLVM Assembly Language
    irtypes is the type system shared by LLVM and SBIL

legispecs/     Attempt to specify the syntax of Wisconsin legislative documents

defn_grammar/       Specs for the Modsplan defn language, used to parse it
                        (Modifications require changes to compiler code)

modsplan/           Python source code of the Modsplan compiler
    
    compiler.py     Compiles source text to target code
    syntax.py       Parses source text into parse tree
    tokenize.py     Tokenizes source text
    grammar.py      Loads grammar specifications
    defn.py         Loads semantic definitions
    parsetree.py    Handles parse trees
    lineparsers.py  Reads lines of source, handles imports, tracks location

test.py             Test suite

linecounts.txt      Line counts of Python code

mycount.py          Line counting scripts
linecount.py

Modsplan To Do List.txt
