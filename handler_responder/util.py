from nltk.tokenize import word_tokenize
from string import punctuation

_PUNCT_TRANS = str.maketrans('', '', punctuation)


def strip_punctuation(s):
    return s.translate(_PUNCT_TRANS)


def tokenize(s):
    return ':'.join(word_tokenize(strip_punctuation(s.lower())))
