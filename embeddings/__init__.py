#!/usr/bin/env python3

import os
from ctypes import cdll, c_char_p, c_void_p


_embeds_interface = cdll.LoadLibrary(os.path.join(os.path.dirname(__file__),
                                                  'embeds.so'))
_embeds_interface.Embeds_create.restype = c_void_p
_embeds_interface.Embeds_loadTxt.argtypes = [c_void_p, c_char_p]
_embeds_interface.Embeds_loadTxt.restype = c_void_p
_embeds_interface.Embeds_loadBin.argtypes = [c_void_p, c_char_p]
_embeds_interface.Embeds_loadBin.restype = c_void_p
_embeds_interface.Embeds_saveTxt.argtypes = [c_void_p, c_char_p]
_embeds_interface.Embeds_saveTxt.restype = c_void_p
_embeds_interface.Embeds_saveBin.argtypes = [c_void_p, c_char_p]
_embeds_interface.Embeds_saveBin.restype = c_void_p
_embeds_interface.Embeds_find.argtypes = [c_void_p, c_char_p]
_embeds_interface.Embeds_find.restype = c_char_p


class Embeds:

    def __init__(self):
        self._embeddings = _embeds_interface.Embeds_create()

    def loadTxt(self, path):
        _embeds_interface.Embeds_loadTxt(self._embeddings,
                                         c_char_p(path.encode('utf-8')))

    def loadBin(self, path):
        _embeds_interface.Embeds_loadBin(self._embeddings,
                                         c_char_p(path.encode('utf-8')))

    def saveTxt(self, path):
        _embeds_interface.Embeds_saveTxt(self._embeddings,
                                         c_char_p(path.encode('utf-8')))

    def saveBin(self, path):
        _embeds_interface.Embeds_saveBin(self._embeddings,
                                         c_char_p(path.encode('utf-8')))

    def find(self, word):
        str_array = _embeds_interface.Embeds_find(self._embeddings,
                                                  c_char_p(word.encode('utf-8')))
        return str_array.decode('utf-8').split(',')
