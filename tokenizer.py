#!/usr/bin/env python3

import sys
import re

emoticon_string = r"""
    (?:
      [<>]?
      [:;=8>xX]                    # eyes
      [\-o\*\']?                 # optional nose
      [\)\]\(\[dDpPxX/\:\}\{@\|\\S] # mouth      
      |
      [\)\]\(\[dDpPxX/\:\}\{@\|\\S] # mouth
      [\-o\*\']?                 # optional nose
      [:;=8<xX]                    # eyes
      [<>]?
      |
      <[/\\]?3                         # heart(added: has)
      |
      \(?\(?\#?                   #left cheeck
      [>\-\^\*\+o\~]              #left eye
      [\_\.\|oO\,]                #nose
      [<\-\^\*\+o\~]              #right eye
      [\#\;]?\)?\)?               #right cheek
    )"""

emoticon_re = re.compile(emoticon_string, re.VERBOSE | re.I | re.UNICODE)

def is_emoticon(token):
    return re.match(emoticon_re, token) is not None

def preprocess(tokens):
    cleaner = list()
    for token in tokens:
        token = re.sub('[`’]', '\'', token)
        if token[:1] == '#' or token[:1] == '@' or 'http' in token:
            cleaner.append(token)
        elif is_emoticon(token):
            cleaner.append(token)
        else:
            for part in re.findall(
                        r"<[UR]>|\d[\d\-/':.,]+\d|\w[\w']*\w|[.,!?;:\"\'()/\\]+|\S",
                        token):
                    if part:
                        if part.isupper() and not re.match(r"<[UR]>", token):
                            cleaner.append(part.lower())
                        else:
                            cleaner.append(part)
    return cleaner


def main(stdin):
    for line in stdin:
        tokens = line.split()
        tokens = preprocess(tokens)
        print(' '.join(tokens))


if __name__ == '__main__':
    main(sys.stdin)
