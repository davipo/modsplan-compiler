
# ModSPLan
## Modular Specification of Programming Languages

Modsplan is a language for writing specifications of programming languages (a [meta-language](http://en.wikipedia.org/wiki/Meta-language)). A Modsplan specification provides a formal definition of the syntax and semantics of a language. These specifications are *modular*: common definitions (for constants, expressions, statements, etc) may be shared between languages.

Modsplan is designed to be readable by humans and computers. Programmers can use a Modsplan spec as a complete formal language reference. The Modsplan compiler reads the same specification in order to compile the defined language. (It is a universal compiler.) This guarantees that the implementation follows the specification (barring compiler bugs).

Three kinds of specifications define a language:

+ a **tokens** grammar specifies how characters of a source text are grouped into tokens
+ a **syntax** grammar defines the language syntax, based on tokens
+ a **defn** (definition) specifies code to generate for each syntactic element

The grammar used in the tokens specs and syntax specs is a simple but powerful 
[BNF](http://en.wikipedia.org/wiki/Backus–Naur_Form) variant. 
The defn spec lists target code instructions to generate for parse tree nodes matching a 
given signature.

Modsplan specifications use three simple languages to define higher-level languages: the Modsplan grammar, the Modsplan defn, and the target instruction set.

To generate code for many platforms, our defn specs usually target SBIL (a Stack-Based Intermediate Language), which will be translated to [LLVM](http://en.wikipedia.org/wiki/LLVM).

