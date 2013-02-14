#!/usr/local/bin/python

# lineparsers.py
# Modsplan line parsers
# Copyright 2013 by David H Post, DaviWorks.com.

import os


""" These parsers offer convenient iteration over lines of text files.
        LineParser tracks current line number, and is a base class for others.
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



class LineParser:
    """ Parses lines of text from file; implements an iterator; tracks line number.
        (Base class for adding other features.)"""
    
    def __init__(self, sourcepath):
        """ Create line parser from text file at sourcepath."""
        self.sourcepath = sourcepath
        self.err = Error(sourcepath)
        self.linenum = 0        # number of lines generated (also current line number)
        
        try:
            sourcetext = open(sourcepath).read()
        except IOError as exc:
            raise self.err.msg('Error loading file ' + sourcepath + '\n' + str(exc))
        
        self.lines = sourcetext.splitlines()


    def __iter__(self):
        """ Returns an iterator of lines of source."""
        return self.generator

    
    def generator(self):
        """ Generator (iterator) of lines of source."""
        for line in lines:
            self.linenum += 1
            yield line
    


class ImportParser(LineParser):
    """ Parses lines of text from file; implements an iterator; tracks line number.
        Imports other files as specified in 'use' directives.
        Keeps a list of imports to avoid repeats and loops."""
    
    def __init__(self, sourcepath):
        """ Create import parser from text file at sourcepath."""
        LineParser.__init__(self, sourcepath)
        self.import_cmd = 'use '
        self.source_dir = os.path.dirname(sourcepath)
        self.extension = os.path.splitext(sourcepath)[1]
        self.imported = [sourcepath]            # list of already imported filepaths

        
    def generator(self):
        """ Generator (iterator) of lines of source; if a line begins with 
            <import_cmd> <import>, return lines of file <import>.ext in place of this line,
            else return line. Imported file uses directory and extension of current file."""
        for line in lines:
            self.linenum += 1
            if line.startswith(self.import_cmd):
                importname = line[len(self.import_cmd):].strip()
                importpath = os.path.join(self.source_dir, importname) + self.extension
                if importpath not in self.imported:
                    self.imported.append(importpath)
                    for import_line in ImportParser(importpath):
                        yield import_line
            else:           
                yield line



class IndentParser(LineParser):
    pass



