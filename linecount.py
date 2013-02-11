#!/usr/local/bin/python

# linecount.py
# Copyright 2012 by David "Davi" Post (DaviWorks.com)

""" Count lines of code in project directory."""

import sys
import os


def linecount(dirpath, extensions=[], nospace=False):
    """ Return (string) table of line counts of files in folder dirpath with extensions.
        If nospace, exclude files whose names include a space."""
    filenames = []
    for fn in os.listdir(dirpath):
        if os.path.splitext(fn)[1] in extensions:
            if nospace and (' ' in fn):
                continue
            else:
                filenames.append(fn)
    
    total_label_format = 'Total (%d files)  '
    fnwidth = max(map(len, filenames + [total_label_format]))
    
    line_format = '%-*s%7s%10s%10s\n'
    table = line_format % (fnwidth, 'Filename', 'Lines', 'Nonblank', '% blank')
    table += '\n'
    
    total = 0
    total_nonblank = 0
    nfiles = 0
    
    for filename in filenames:
        f = open(os.path.join(dirpath, filename))
        lines = f.readlines()
        
        numlines = len(lines)
        total += numlines
        
        lines = [line.strip() for line in lines]
        blank = lines.count('')
        
        pct_blank = (int(round(blank * 100.0 / numlines)) if numlines else 0)
        
        nonblank = numlines - blank
        total_nonblank += nonblank
        
        table += line_format % (fnwidth, filename, numlines, nonblank, pct_blank)
        nfiles += 1
        
    table += '\n'
    total_label = total_label_format % nfiles
    
    blank = total - total_nonblank
    pct_blank = int(round(blank * 100.0 / total))
    
    table += line_format % (fnwidth, total_label, total, total_nonblank, pct_blank)
    return table


if __name__ == '__main__':
    if len(sys.argv) >= 2:
        program_name, dirpath = sys.argv[:2]
        print linecount(dirpath, sys.argv[2:])
    else:
        print 'Usage: %s <folder> <ext>*' % program_name
        print '    Counts lines of files in folder [with specified extensions].'
