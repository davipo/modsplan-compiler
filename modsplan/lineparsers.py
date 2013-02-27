#!/usr/local/bin/python

# lineparsers.py
# Modsplan line parsers
# Copyright 2013 by David H Post, DaviWorks.com.

import os


""" These parsers offer convenient iteration over lines of text.
        LineParser tracks current line number.
        IndentParser tracks indentation level.
        FileParser reads lines from a file.
        ImportParser handles importing lines from other files.
"""

import_command = 'use '

class Error(Exception):
    pass


class LineParser(object):
    """ Serves lines of text from an iterator of strings; 
        implements an iterator; tracks line number."""
    
    def __init__(self, iterator):
        """ Create line parser from iterator of strings (one per line);
            linenum attribute gives line number of last line served (starting at 1)."""
        self.iterator = iterator
        self.linenum = 0        # number of lines generated (also current line number)
        
    def __iter__(self):
        """ Returns an iterator of lines of source."""
        return self.generator()
        
    def generator(self):
        """ Generator (iterator) of lines of source."""
        for line in self.iterator:
            self.linenum += 1
            for procline in self.process_line(line):
                yield procline
    
    def process_line(self, line):
        """ Generator of processed lines. Perform any processing on line,
            yield resulting lines. (Override in subclasses.)"""
        yield line
    
    def readlines(self):
        """ Return list of remaining lines, each terminated with '\n'."""
        return ['%s\n' % line for line in self.generator()]
    
    def error(self, message):
        """ Return Error containing message; append line number if nonzero."""
        if self.linenum:
            message += ' in line %d' % self.linenum
        return Error(message)


class IndentParser(LineParser):
    """ Serves lines of text from an iterator of strings; 
        implements an iterator; tracks line number and indentation level.
        Strict indentation rules (IndentationError raised if violated):
            Only tab ('\t') or space chars may indent a line, they may not be mixed.
            First indent may be one tab char or a string of spaces.
            All indents must be a multiple of the first."""
    
    def __init__(self, iterator, track_indent=True):
        """ Create indentation parser from iterator of strings (one per line);
            linenum attribute gives line number of last line served (starting at 1).
            If track_indent, level attribute gives indentation level of last line served."""
        LineParser.__init__(self, iterator)
        self.track_indent = track_indent    # set False to disable level computation
        self.level = 0                      # indentation level
        self.indent = ''                    # indent chars: one tab or string of spaces
    
    def process_line(self, line):
        """ Track indentation level, raise Error if inconsistent.
            (Generator of processed lines, yields orginal line unchanged.)"""
        if self.track_indent and line.strip():      # line of whitespace doesn't affect level
            # compute indentation level
            indentstr = self.indentation(line)      # all the whitespace at start of line
            if len(indentstr) == 0:
                self.level = 0
            elif self.indent:
                # not first indent, check that indent is multiple of first indent
                self.level, extra = divmod(len(indentstr), len(self.indent))
                if not indentstr.startswith(self.indent) or extra != 0:
                    raise self.error('Indent is not a multiple of first indent')
            else:
                # this is first indent, set indent string for current text
                self.indent = indentstr
                self.level = 1
        yield line
    
    def indentation(self, line):
        """ Return string of all whitespace at start of line;
            check that it contains either only tab chars or only space chars,
            otherwise raise Error."""
        length = len(line) - len(line.lstrip())
        whitespace = line[:length]
        if whitespace:
            first = whitespace[0]
            if first not in (' ', '\t') or any(char != first for char in whitespace):
                raise self.error('Bad indentation, must be all tabs or all spaces')
        return whitespace
    

class FileParser(IndentParser):
    """ Serves lines of text from file; implements an iterator; 
        tracks line number. Lines served without line end chars.
        Option to track indentation (see IndentParser), disabled by default."""
    
    def __init__(self, sourcepath, track_indent=False):
        """ Create line parser from text file at sourcepath.
            Option to track indentation (see IndentParser), disabled by default."""
        self.sourcepath = sourcepath
        try:
            sourcetext = open(sourcepath).read()
        except IOError as exc:
            raise Error('Error loading file ' + sourcepath + '\n' + str(exc))
        lines = sourcetext.splitlines()
        IndentParser.__init__(self, lines, track_indent)

    def error(self, message):
        """ Return Error with message; append current filepath, & line number if nonzero."""
        message += ' in '
        if self.linenum:
            message += 'line %d of ' % self.linenum
        message += self.sourcepath
        return Error(message)


class ImportParser(FileParser):
    """ Serves lines of text (without line end chars) from file; 
            implements an iterator; tracks line number.
        Recursively includes other files as specified in import commands,
            keeping a list of imports to avoid repeats and loops.
        Option to track indentation level."""
    
    def __init__(self, sourcepath, track_indent=False, imported=None):
        """ Create import parser from text file at sourcepath.
            Option to track indentation (see IndentParser), disabled by default.
            Optional param 'imported' is a list of filepaths already imported.
            Yields (line, info), info has attributes linenum, (indent) level, sourcepath.
        """
        FileParser.__init__(self, sourcepath, track_indent)
        if imported == None:
            imported = []
        self.imported = imported                # list of already imported filepaths
        self.imported.append(sourcepath)
        self.source_dir = os.path.dirname(sourcepath)
        self.extension = os.path.splitext(sourcepath)[1]

    def process_line(self, line):
        """ Generator of processed lines. If a line begins <import_command> <import>,
            yield lines of file <import>.ext in place of this line, else yield line. 
            Imported file uses directory and extension of parent file.
            Yields (line, info), info has attributes linenum, (indent) level, sourcepath.
        """
        # overriding FileParser.process_line(), so do its processing first
        for pline in FileParser.process_line(self, line):
            if pline.startswith(import_command):
                pline = pline.partition('#')[0]     # remove any comment
                importname = pline[len(import_command):].strip()
                importpath = os.path.join(self.source_dir, importname) + self.extension
                if importpath not in self.imported:
                    importer = ImportParser(importpath, self.track_indent, self.imported)
                    for import_line in importer:
                        yield import_line
            else:
                yield (pline, self)


class LineInfoParser(LineParser):
    """ Simplifies access to line data, yielding line text directly.
        Serves lines of text (without line end chars) from file; 
            implements an iterator; tracks line number.
        Recursively includes other files as specified in import commands,
            keeping a list of imports to avoid repeats and loops.
        Option to track indentation level."""
    
    def __init__(self, sourcepath, track_indent=False):
        """ Create line parser from text file at sourcepath.
            Option to track indentation (see IndentParser), disabled by default."""
        self.parser = ImportParser(sourcepath, track_indent)
        # line info, updated for each line served
        self.linenum = 0
        self.level = 0
        self.sourcepath = sourcepath
        self.info = self.parser
           
    def generator(self):
        """ Generator (iterator) of lines of source."""
        for line, info in self.parser:
            self.linenum = info.linenum
            self.level = info.level
            self.sourcepath = info.sourcepath
            self.info = info
            yield line

    def error(self, message):
        """ Return Error with message; append current filepath, & line number if nonzero."""
        return self.info.error(message)


def test_parse(sourcepath):
    lines = LineInfoParser(sourcepath, track_indent=True)
    for line in lines:
        filename = os.path.basename(lines.sourcepath)
        print '%20s %2d %1d %s' % (filename, lines.linenum, lines.level, line)


sp = 'sample_source/' + 'simplepy.L0'
ra = 'sample_source/' + 'reassemble.py'
rt = 'sample_source/' + 'reassemble_tabbed.py'
it = 'sample_source/' + 'import_test.L0'

