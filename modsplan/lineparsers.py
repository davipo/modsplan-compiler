#!/usr/local/bin/python

# lineparsers.py
# Modsplan line parsers
# Copyright 2013 by David H Post, DaviWorks.com.

import os


""" These parsers offer convenient iteration over lines of text.
        LineParser tracks current line number.
        FileParser reads lines from a file.
        ImportParser handles importing lines from other files.
        IndentParser tracks indentation level.
"""


class Error(Exception):
    """ Convenient error reporting."""
    
    def __init__(self, filename=None):
        self.filename = filename        # current filename (where errors found)
        self.message = ''

    def __str__(self):
        return self.message

    def msg(self, message, linenum=None, column=None):
        """ Add message. If line number specified, add it and filename to message;
            if column, insert that. Return self.
        """
        if linenum:
            message += ' in line %d' % linenum
            if column:
                message += ', column %s' % column
            message += ' of %s' % self.filename
        self.message = message
        return self


class LineParser(object):
    """ Serves lines of text from an iterator of strings; 
        implements an iterator; tracks line number."""
    
    def __init__(self, iterator):
        """ Create line parser from iterator of strings (one per line)."""
        self.iterator = iterator
        self.linenum = 0        # number of lines generated (also current line number)
        
    def __iter__(self):
        """ Returns an iterator of lines of source."""
        return self.generator()
        
    def generator(self):
        """ Generator (iterator) of lines of source."""
        for line in self.iterator:
            self.linenum += 1
            yield line
    
    def readlines(self):
        """ Return list of remaining lines, each terminated with '\n'."""
        return ['%s\n' % line for line in self.generator()]
    

class FileParser(LineParser):
    """ Parses lines of text from file; implements an iterator; tracks line number."""
    
    def __init__(self, sourcepath):
        """ Create line parser from text file at sourcepath."""
        self.sourcepath = sourcepath
        self.err = Error(sourcepath)
        try:
            sourcetext = open(sourcepath).read()
        except IOError as exc:
            raise self.err.msg('Error loading file ' + sourcepath + '\n' + str(exc))
        lines = sourcetext.splitlines()
        LineParser.__init__(self, lines)


class ImportParser(FileParser):
    """ Parses lines of text from file; implements an iterator; tracks line number.
        Imports other files as specified in 'use' directives.
        Keeps a list of imports to avoid repeats and loops."""
    
    def __init__(self, sourcepath, imported=[]):
        """ Create import parser from text file at sourcepath;
            optional param 'imported' is a list of filepaths already imported."""
        FileParser.__init__(self, sourcepath)
        self.import_cmd = 'use '
        self.source_dir = os.path.dirname(sourcepath)
        self.extension = os.path.splitext(sourcepath)[1]
        self.imported = imported                # list of already imported filepaths
        self.imported.append(sourcepath)

        
    def generator(self):
        """ Generator (iterator) of lines of source; if a line begins with 
            <import_cmd> <import>, return lines of file <import>.ext in place of this line,
            else return line. Imported file uses directory and extension of current file."""
        for line in self.iterator:
            self.linenum += 1
            if line.startswith(self.import_cmd):
                importname = line[len(self.import_cmd):].strip()
                importpath = os.path.join(self.source_dir, importname) + self.extension
                if importpath not in self.imported:
                    self.imported.append(importpath)
                    for import_line in ImportParser(importpath, self.imported):
                        yield import_line
            else:           
                yield line



class IndentParser(LineParser):
    pass

## Read iterator once, track indentation as we go.






