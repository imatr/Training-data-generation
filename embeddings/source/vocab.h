#ifndef INCLUDED_VOCAB_
#define INCLUDED_VOCAB_

#include <string>
#include <set>
#include <vector>
#include <stdint.h>
#include <fstream>
#include <utility>

class Vocab
{
    std::set<std::string> d_collect; // Only temporary

    std::vector<char> d_vocab;
    std::vector<uint32_t> d_idxs;

    public:
        Vocab();
        Vocab(std::string const &path, bool bin = false);
        Vocab(std::ifstream *ifs);

        void saveBin(std::string const &path);
        void saveBin(std::ofstream *ofs);
        void loadBin(std::string const &path);
        void loadBin(std::ifstream *ifs);

        void save(std::string const &path);
        void save(std::ofstream *ofs);
        void load(std::string const &path);
        void load(std::ifstream *ofs);
        void loadOrdered(std::string const &path);
        void loadOrdered(std::ifstream *ofs);

        void addWord(std::string const &word);
        void addOrdered(std::string const &word);
        void optimize(); // mv words from set to vocab
        void clear();

        uint32_t getId(std::string const &word);
        uint32_t getId(uint32_t beg, uint32_t end, char const *searchWord);
        bool contains(std::string const &word);
        char *getWord(uint32_t id);
        uint32_t size(){return d_idxs.size() - 1;};

        std::pair<uint32_t, uint32_t> getRange(char const *word);
        uint32_t findBeg(uint32_t beg, uint32_t end, char const *word);

    private:

};

#endif
