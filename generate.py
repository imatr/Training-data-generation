#!/usr/bin/env python3

import sys
import re
import gzip
import argparse
import os
import json
from xml.sax.saxutils import unescape

import kenlm

from embeddings import Embeds


class BrownClusters:

    def __init__(self, paths, vocab, force_oov=False):
        self.path_dict = dict()
        self.token_dict = dict()
        self._most_common = dict()
        with open(paths, 'r', encoding='utf-8', newline='\n') as f:
            for line in f:
                path, token, count = line.split('\t')
                count = int(count)
                if path not in self.path_dict:
                    self.path_dict[path] = set()
                    self._most_common[path] = ('', 0)
                is_iv = vocab.contains_word(token)
                if force_oov:
                    is_iv = not is_iv
                if is_iv:
                    if count > self._most_common.get(path, ('', 0))[1]:
                        self._most_common[path] = token, count
                    self.path_dict[path].add(token)
                self.token_dict[token] = path

    def suggest(self, token):
        if token not in self.token_dict:
            return set()
        return self.path_dict[self.token_dict[token]]

    def get_path(self, token):
        return self.token_dict.get(token, '')

    def most_common(self, path):
        return self._most_common.get(path, '')[0]


class SuggestionTree:

    def __init__(self, delimiter=';', ignore_case=False):
        self.contents = dict()
        self.delimiter = delimiter
        self.ignore_case = ignore_case

    def add_word(self, word):
        if self.contains_word(word):
            return
        if self.ignore_case:
            word = word.lower()
        word = self.delimiter + word + self.delimiter
        current_dict = self.contents
        for letter in word:
            if letter not in current_dict:
                current_dict[letter] = dict()
            current_dict = current_dict[letter]

    def add_words(self, list_of_words):
        for word in list_of_words:
            self.add_word(word)

    def contains_word(self, word):
        if self.ignore_case:
            word = word.lower()
        word = self.delimiter + word + self.delimiter
        try:
            current_dict = self.contents
            for letter in word:
                current_dict = current_dict[letter]
            return True
        except KeyError:
            return False

    def suggest(self, word, depth=2):
        if self.ignore_case:
            word = word.lower()
        word = word + self.delimiter
        # Position, current word, part of the tree, depth
        paths = [(0, '', self.contents.get(self.delimiter, dict()), 0)]
        results = set()
        while paths:
            index, current_part, current_dict, current_depth = paths.pop()
            if index == len(word):
                continue
            next_letter = word[index]
            for letter_option in current_dict:
                if letter_option == next_letter:
                    # Correct path
                    if letter_option == self.delimiter:
                        # Result found
                        results.add(current_part)
                    else:
                        # Going towards goal
                        paths.append((index+1,
                                      current_part+next_letter,
                                      current_dict[next_letter],
                                      current_depth))
                elif current_depth < depth:
                    # Insertion
                    paths.append((index,
                                  current_part+letter_option,
                                  current_dict[letter_option],
                                  current_depth+1))
                    # Substitution
                    paths.append((index+1,
                                  current_part+letter_option,
                                  current_dict[letter_option],
                                  current_depth+1))
            if current_depth < depth:
                # Deletion
                paths.append((index+1,
                              current_part,
                              current_dict,
                              current_depth+1))
        return results


class Scorer:

    def __init__(self, language_model):
        self.model = language_model

    @staticmethod
    def levenshtein(token1, token2):
        if not token1 and not token2:
            return 0
        elif not token1:
            return len(token2)
        elif not token2:
            return len(token1)
        matrix = [[i for i in range(len(token2) + 1)]]
        for i, char1 in enumerate(token1):
            matrix.append([i+1])
            for j, char2 in enumerate(token2):
                possibilities = []
                possibilities.append(matrix[i][j+1] + 1)
                possibilities.append(matrix[i][j] + (not char1 == char2))
                if i+1 < len(matrix):
                    possibilities.append(matrix[i+1][j] + 1)
                matrix[i+1].append(min(possibilities))
        return matrix[i+1][j+1]

    def best_match(self, token, suggestions, previous_word, next_word):
        best_match = '', 0
        if not token:
            return best_match
        for suggestion in suggestions:
            prior_probability = 10**self.model.score('{} {} {}'.format(
                    previous_word, suggestion, next_word),
                    bos=(previous_word == ''),
                    eos=(next_word == ''))
            distance = Scorer.levenshtein(token, suggestion)
            ratio = distance / len(token)
            # Same token, very likely to be correct
            if ratio == 0:
                ratio = 5
            score = prior_probability / ratio
            if not best_match[1] or score > best_match[1]:
                best_match = suggestion, score
        return best_match

    @staticmethod
    def abbreviation_score(abbreviation, token):
        if not abbreviation:
            return 0
        max_score = 0
        for start in range(len(abbreviation)):
            goal = abbreviation[start]
            score = 0
            for letter in token:
                if letter == goal:
                    score += 1
                    if start+score == len(abbreviation):
                        break
                    goal = abbreviation[start+score]
            if score > max_score:
                max_score = score
            if score == len(abbreviation):
                break
        return max_score / len(abbreviation)

    @staticmethod
    def abbreviation_best_matches(abbreviation, suggestions):
        best_score = 0
        best = set()
        for suggestion in suggestions:
            score = Scorer.abbreviation_score(abbreviation, suggestion)
            if score > best_score:
                best = {suggestion}
                best_score = score
            elif score == best_score:
                best.add(suggestion)
        return best, best_score

    @staticmethod
    def abbreviation_best_matches_reverse(full_word, suggestions):
        best_score = 0
        best = set()
        for suggestion in suggestions:
            score = Scorer.abbreviation_score(suggestion, full_word)
            if score > best_score:
                best = {suggestion}
                best_score = score
            elif score == best_score:
                best.add(suggestion)
        return best, best_score


class TweetJsonReader:

    def __init__(self, *paths):
        self.paths = paths

    def readlines(self):
        for path in self.paths:
            with gzip.open(path, 'rt', encoding='utf-8') as f:
                for line in f:
                    data = json.loads(line.strip())
                    if 'retweeted_status' not in data:
                        if 'extended_tweet' in data:
                            text = unescape(data.get('extended_tweet').get('full_text'))
                            yield re.sub('\n+', ' ', text)
                        elif not data.get('truncated'):
                            yield unescape(re.sub('\n+', ' ', data.get('text')))


class Writer:

    def __init__(self, path):
        self.path = path

    def __enter__(self):
        self.file = open(self.path, 'w', newline='\n')
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.file.close()
        return False

    def writeTokenPair(self, original, normalized, status='-'):
        print('{}\t{}\t{}'.format(original, status, normalized), file=self.file)

    def newline(self):
        print(file=self.file)


class Preprocessor:

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

    @staticmethod
    def is_emoticon(token):
        return re.match(Preprocessor.emoticon_re, token) is not None

    @staticmethod
    def preprocess(tokens):
        cleaner = list()
        for token in tokens:
            token = re.sub('[`’]', '\'', token)
            if token[:1] == '#' or token[:1] == '@' or 'http' in token:
                cleaner.append(token)
            elif Preprocessor.is_emoticon(token):
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


class SourceTracer:

    def __init__(self):
        self.word_sources = dict()

    def clear(self):
        self.word_sources = dict()

    def add_trace(self, source, identifier, *words):
        for word in words:
            word = '{}:{}'.format(word, identifier)
            if word not in self.word_sources:
                self.word_sources[word] = set()
            self.word_sources[word].add(source)

    def get_sources(self, identifier, word):
        word = '{}:{}'.format(word, identifier)
        return self.word_sources.get(word, set())


def noisify(tweet, iv, tokens):
    tracer = SourceTracer()
    original = iv.copy()
    scores = dict()
    suggestion_log = dict()
    for index, token in iv.items():
        suggestions = set()
        previous_token = tokens[index-1] if index > 0 else ''
        next_token = tokens[index+1] if index+1 < len(tokens) else ''

        # Brown cluster suggestions
        brown_suggestions = noisy_clusters.suggest(token)
        if brown_suggestions:
            # Abbreviation suggestions (can be multiple)
            best_abbreviations, score = Scorer.abbreviation_best_matches_reverse(
                    token,
                    brown_suggestions)
            if score > 0.7:
                suggestions |= best_abbreviations
                tracer.add_trace('Brown cluster (abbreviation)', index, *best_abbreviations)
            # Most common IV token in cluster
            most_common = noisy_clusters.most_common(clusters.get_path(token))
            if most_common:
                suggestions.add(most_common)
                tracer.add_trace('Brown cluster (most common OOV)', index, most_common)

        # Word embedding suggestions
        for possible_suggestion in embeddings.find(token):
            if possible_suggestion and not spelling.contains_word(possible_suggestion):
                suggestions.add(possible_suggestion)
                tracer.add_trace('word-embeddings', index, possible_suggestion)
                break

        # Split word
        if args.allow_compounds:
            word_combination = None
            for i in range(2, len(token)-2):
                if spelling.contains_word(token[:i]) \
                        and spelling.contains_word(token[i:]):
                    phrase = '{} {}'.format(token[:i], token[i:])
                    suggestions.add(phrase)
                    tracer.add_trace('word split', index, phrase)

        # Select candidate, and filter some illegal matches, such as hashtags
        best_suggestion = token
        best_score = language_model.score('{} {} {}'.format(
                previous_token, token, next_token),
                bos=(previous_token == ''),
                eos=(next_token == '')) * 2
        for suggestion in suggestions:
            if suggestion[:1] == '#' or suggestion[:1] == '@':
                continue
            score = language_model.score('{} {} {}'.format(
                    previous_token, suggestion, next_token),
                    bos=(previous_token == ''),
                    eos=(next_token == ''))
            if score > best_score:
                best_score = score
                best_suggestion = suggestion
        if best_suggestion != token and len(tracer.get_sources(index, best_suggestion)) >= 2:
            iv[index] = best_suggestion
            scores[index] = best_score
            suggestion_log[index] = suggestions
    if iv == original:
        return

    # Write output
    noisyfied = list()
    for index, token in enumerate(tokens):
        if index in iv:
            noisyfied.append(iv[index])
        else:
            noisyfied.append(token)
    for original_token, noisyfied_token in zip(tokens, noisyfied):
        change = 'IV' if original_token == noisyfied_token else 'OOV'
        out_clean.writeTokenPair(noisyfied_token, original_token, change)
    out_clean.newline()

    # Calculate probability, as a sort of confidence score
    sentence_probability = language_model.score(' '.join(noisyfied), bos=True, eos=True)

    # print debug info
    if args.debug:
        print('NOISYFIED')
        print(tweet)
        print(tokens)
        for index, token in original.items():
            if iv[index] != original[index]:
                print('{} -> {} ({}, {})'.format(token,
                                                 iv[index],
                                                 scores[index],
                                                 suggestion_log[index]))
                sources = tracer.get_sources(index, iv[index])
                print('Sources: {}'.format(', '.join(sources)))
        print('Sentence probability: {:.5f}'.format(score))
        if score:
            input()
        else:
            print()

    return sentence_probability


def clean(tweet, oov, tokens):
    tracer = SourceTracer()
    original = oov.copy()
    scores = dict()
    suggestion_log = dict()
    for index, token in oov.items():
        suggestions = set()
        previous_token = tokens[index-1] if index > 0 else ''
        next_token = tokens[index+1] if index+1 < len(tokens) else ''
        if index-1 in oov:  # If the previous token has been normalized, use the replacement
            previous_token = oov[index-1]

        # typo suggestion
        typo_suggestions = spelling.suggest(token, 1)
        if not typo_suggestions:
            typo_suggestions = spelling.suggest(token, 2)
        if typo_suggestions:
            best_match, score = distance_scorer.best_match(token,
                                                           typo_suggestions,
                                                           previous_token,
                                                           next_token)
            suggestions.add(best_match)
            tracer.add_trace('typo', index, best_match)

        # Word embedding suggestions
        for possible_suggestion in embeddings.find(token):
            if possible_suggestion and spelling.contains_word(possible_suggestion):
                suggestions.add(possible_suggestion)
                tracer.add_trace('word-embeddings', index, possible_suggestion)
                break

        # Brown cluster suggestions
        brown_suggestions = clusters.suggest(token)
        if brown_suggestions:
            # Abbreviation suggestions (can be multiple)
            best_abbreviations, score = Scorer.abbreviation_best_matches(token, brown_suggestions)
            if score > 0.7:
                suggestions |= best_abbreviations
                tracer.add_trace('Brown cluster (abbreviation)', index, *best_abbreviations)
            # Most common IV token in cluster
            most_common = clusters.most_common(clusters.get_path(token))
            if most_common:
                suggestions.add(most_common)
                tracer.add_trace('Brown cluster (most common IV)', index, most_common)

        # Shorten (fix lengthening)
        if len(token) > 3:
            shortened = re.sub(r'(\w)\1+', r'\1\1', token)
            if spelling.contains_word(shortened):
                suggestions.add(shortened)
                tracer.add_trace('shortening', index, shortened)
            shortened = re.sub(r'(\w)\1+', r'\1', token)
            if spelling.contains_word(shortened):
                suggestions.add(shortened)
                tracer.add_trace('shortening', index, shortened)

        # Split word
        if not args.allow_compounds:
            word_combination = None
            for i in range(2, len(token)-2):
                if spelling.contains_word(token[:i]) \
                        and spelling.contains_word(token[i:]):
                    phrase = '{} {}'.format(token[:i], token[i:])
                    suggestions.add(phrase)
                    tracer.add_trace('word split', index, phrase)

        # Select candidate
        best_suggestion = token
        best_score = language_model.score('{} {} {}'.format(
                previous_token, token, next_token),
                bos=(previous_token == ''),
                eos=(next_token == ''))
        for suggestion in suggestions:
            score = language_model.score('{} {} {}'.format(
                    previous_token, suggestion, next_token),
                    bos=(previous_token == ''),
                    eos=(next_token == ''))
            if score > best_score:
                best_score = score
                best_suggestion = suggestion
        if best_suggestion != token and len(tracer.get_sources(index, best_suggestion)) >= 2:
            oov[index] = best_suggestion
            scores[index] = best_score
            suggestion_log[index] = suggestions
        else:
            return 0

    # Write output
    cleaned = list()
    for index, token in enumerate(tokens):
        if index in oov:
            cleaned.append(oov[index])
        else:
            cleaned.append(token)
    for original_token, cleaned_token in zip(tokens, cleaned):
        change = 'IV' if original_token == cleaned_token else 'OOV'
        out_noisy.writeTokenPair(original_token, cleaned_token, change)
    out_noisy.newline()

    # Calculate probability, as a sort of confidence score
    sentence_probability = language_model.score(' '.join(cleaned), bos=True, eos=True)

    # print debug info
    if args.debug:
        print('CLEANED')
        print(tweet)
        print(tokens)
        for index, token in original.items():
            if index in oov:
                print('{} -> {} ({}, {})'.format(token,
                                                 oov[index],
                                                 scores[index],
                                                 suggestion_log[index]))
                sources = tracer.get_sources(index, oov[index])
                print('Sources: {}'.format(', '.join(sources)))
        print('Sentence probability: {:.5f}'.format(score))
        if score:
            input()
        else:
            print()

    # Return the probability of the sentence
    return sentence_probability


def main(args):
    print('Processing', file=sys.stderr)
    for tweet in input_file:
        tokens = tweet.split()
        if tokens and (tokens[-1] == '…' or tokens[-1] == ['...']):
             continue
        oov = dict()
        iv = dict()
        tokens = Preprocessor.preprocess(tokens)
        for index, token in enumerate(tokens):
            # Non-words, emoticons, emoji, etc
            if not re.search(r'[a-zA-Z]', token) or Preprocessor.is_emoticon(token):
                continue
            # Users, hashtags, urls
            if re.match(r"<[UR]>", token) or token[:1] == '#' or token[:1] == '@' or 'http' in token:
                continue
            # Names
            if index != 0 and len(token) >= 2 and token[0].isupper() and not token[1].isupper():
                continue
            # Compound words
            if args.allow_compounds:
                compound = False
                for i in range(2, len(token)-2):
                    if spelling.contains_word(token[:i]) and spelling.contains_word(token[i:]):
                        compound = True
                        break
                if compound:
                    continue
            # OOV tokens
            if not spelling.contains_word(token):
                oov[index] = token
            else:
                iv[index] = token
        if len(oov) == 0:
            noisify(tweet, iv, tokens)
        else:
            score = clean(tweet, oov, tokens)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--data',
                        help='The file containing tweets',
                        required=True)
    parser.add_argument('--vocabulary',
                        help='A list containing IV words',
                        required=True)
    parser.add_argument('--paths',
                        help='Brown cluster paths',
                        required=True)
    parser.add_argument('--model',
                        help='Language model',
                        required=True)
    parser.add_argument('--embeddings',
                        help='Path to cached word embeddings',
                        required=True)
    parser.add_argument('--allow-compounds',
                        action='store_true',
                        help='Allows words to be chained together without a space')
    parser.add_argument('--output-clean',
                        help='The file to write noisified token pairs to',
                        required=True)
    parser.add_argument('--output-noisy',
                        help='The file to write cleaned token pairs to',
                        required=True)
    parser.add_argument('--debug',
                        action='store_true',
                        help='Print debug information',
                        required=False)
    args = parser.parse_args()
    spelling = SuggestionTree(ignore_case=True)
    language_model = kenlm.Model(args.model)
    distance_scorer = Scorer(language_model)
    embeddings = Embeds()
    embeddings.loadBin(args.embeddings)
    print('Initializing', file=sys.stderr)
    with open(args.vocabulary, 'r', encoding='utf-8', newline='\n') as f:
        for line in f:
            spelling.add_word(line.rstrip())
    clusters = BrownClusters(args.paths, spelling, force_oov=False)
    noisy_clusters = BrownClusters(args.paths, spelling, force_oov=True)
    with open(args.data, 'r', encoding='utf-8', newline='\n') as input_file, Writer(args.output_noisy) as out_noisy, Writer(args.output_clean) as out_clean:
        main(args)
