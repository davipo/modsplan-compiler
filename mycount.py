#!/usr/local/bin/python

import linecount

import modsplan.__init__ as pkg


if __name__ == '__main__':
    pkgdir = pkg.__name__.partition('.')[0]
    header = '\nLine count for %s version %s:\n'
    header %= (pkgdir, pkg.__version__)
    
    table = header + linecount.linecount(pkgdir, ['.py'], nospace=True)
    
    with open('linecounts.txt', 'a') as count_file:
        count_file.write(table + '\n')
    
    print table
    
