# Distant supervision for lexical normalization
## Generating training data in multiple languages

This repository contains code and related files for my master thesis about distant supervision for lexical normalization.

## Generating training data

To generate annotated training data, you'll need a few things:
* A large amount of raw twitter data in the language of interest
* A vocabulary file containing all words which should be considered correct
* [KenLM](https://kheafield.com/code/kenlm/)
* [A tool to perform Brown clustering](https://github.com/percyliang/brown-cluster/)
* Cached word embeddings (included in [MoNoise models](http://robvandergoot.com/data/monoise/), see https://bitbucket.org/robvanderg/monoise/src/master/)

_Most of the required files are already provided for English, Spanish, Dutch, and Serbian. For those languages, You will only need the cached word embeddings and a large amount of raw data_

First, you should tokenize your tweets using the tokenizer provided in this repository. The tokenized tweets should then be clustered using the Brown clustering tool by Percy Liang. You should also create a language model using KenLM. I've used an order 3 language model, but other orders should also work.

Now that you have all required data, you should run the generation system. This can be done using the following command:
```{bash}
$ python3 generate.py \
--data <path to your non-tokenized tweets> \
--vocabulary vocabularies/<language> \
--paths <path to your Brown clusters>/paths \
--model <path to your KenLM model> \
--embeddings <path to your cached embeddings (.cached.bin extension)> \
--output-noisy <output file for automatically normalized tweets> \
--output-clean <output file for tweets with added noise>
```
_Please note that the output will be overwritten without asking when running the system multiple times._

