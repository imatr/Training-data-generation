#include "vocab.h"

#include <string.h>
#include <iostream>
#include <sstream>

using namespace std;

Vocab::Vocab()
//:
{
    d_idxs.push_back(0);
}

Vocab::Vocab(string const &path, bool bin)
//:
{
    if (bin)
        loadBin(path);
    else
        load(path);
}

Vocab::Vocab(ifstream *ifs)
//:
{
    loadBin(ifs);
}

void Vocab::clear()
{
    std::set<std::string> tmp;
    d_collect.swap(tmp);

    d_vocab.clear();
    d_idxs.clear();
    d_idxs.push_back(0);
}

void Vocab::load(string const &path)
{
    ifstream in(path);
    if (!in.good())
    {
        cerr << "Could not read vocab: " << path << '\n';
        exit(1);
    }

    load(&in);
}

void Vocab::load(ifstream *ifs)
{
    string word;
    while(getline((*ifs), word))
        addWord(word);
    optimize();
}

void Vocab::save(string const &path)
{
    ofstream ofs(path);
    if (!ofs.good())
    {
        cerr << "Could not write vocab: " << path << '\n';
        exit(1);
    }
    save(&ofs);
}

void Vocab::save(ofstream *ofs)
{
    if (d_idxs.size() <= 1)
        return;
    for (uint32_t wordIdx = 1; wordIdx != d_idxs.size(); ++wordIdx)
    {
        (*ofs) << &d_vocab[d_idxs[wordIdx]] << '\n';
    }
}

uint32_t Vocab::getId(string const &target)
{
    return getId(0, d_idxs.size()-1, &target[0]);
}

uint32_t Vocab::getId(uint32_t beg, uint32_t end, char const *searchWord)
{
    uint32_t split = (end + beg) / 2;
    uint32_t begIdx = d_idxs[split];

    int comp = strcmp(searchWord, &d_vocab[begIdx]);
    
    //TODO this should be possible with less ifs
    if (beg == split && end == beg + 1)
        return getId(end, end, searchWord);
    if (beg == split && split == end)
        return (comp ==0)?beg:0;
    if (beg == end || beg == split)
        return 0;
    if (comp > 0)
        return getId(split, end, searchWord);
    if (comp < 0)
        return getId(beg, split, searchWord);
    return split;
}

void Vocab::addWord(string const &word)
{
    //emplace?
    d_collect.insert(word);
}

uint32_t Vocab::findBeg(uint32_t beg, uint32_t end, char const *searchWord)
{
    uint32_t split = (end + beg) / 2;
    uint32_t lenSplit = strlen(&d_vocab[d_idxs[split]]);
    uint32_t lenSearchword = strlen(searchWord);

    if (lenSplit > lenSearchword)
        lenSplit = lenSearchword;

    int comp = strncmp(searchWord, &d_vocab[d_idxs[split]], lenSplit);
    int comp2 = strncmp(searchWord, &d_vocab[d_idxs[split]], lenSearchword);
    if (comp2 == 0)
        return split;
    if (lenSplit < lenSearchword)
    {
        comp = strcmp(searchWord, &d_vocab[d_idxs[split]]);
    }
    if (beg == end || beg == split)
        return 0;
    if (comp > 0)
        return findBeg(split, end, searchWord);
    if (comp < 0)
        return findBeg(beg, split, searchWord);
    return split;
}

char *Vocab::getWord(uint32_t id)
{
    return &d_vocab[d_idxs[id]];
}

bool Vocab::contains(string const &target)
{
    return getId(target) != 0; 
}

pair<uint32_t, uint32_t> Vocab::getRange(char const *word)
{
    uint32_t beg = findBeg(0, d_idxs.size()-1, word);
    if (beg == 0)
        return make_pair(0,0);
    
    size_t end = beg;
    for (;beg != 0; --beg)
        if (strncmp(word, &d_vocab[d_idxs[beg]], strlen(word))!= 0)
            break;
    
    for (; end != d_idxs.size(); ++end)
        if(strncmp(word, &d_vocab[d_idxs[end]], strlen(word))!= 0)
            break;

    return make_pair(beg + 1, end);
}

void Vocab::loadBin(string const &path)
{
    ifstream ifs(path, ios::binary);
    if (!ifs.good())
    {
        cerr << "Could not read vocab: " << path << '\n';
        exit(1);
    }

    loadBin(&ifs);
    ifs.close();
}

void Vocab::loadBin(ifstream *ifs)
{
    uint64_t size;
    ifs->read(reinterpret_cast<char*>(&size), sizeof(uint64_t));
    d_vocab = vector<char>(size);
    ifs->read(&d_vocab[0], sizeof(char) * size);

    ifs->read(reinterpret_cast<char*>(&size), sizeof(uint64_t));
    d_idxs = vector<uint32_t>(size);
    ifs->read(reinterpret_cast<char*>(&d_idxs[0]), sizeof(uint32_t) * size);
}

void Vocab::optimize()
{
    if (d_idxs.size() > 1)
        for (size_t beg = 1; beg != d_idxs.size(); ++beg)
            d_collect.insert(string(&d_vocab[d_idxs[beg]]));
    d_vocab.clear();
    d_idxs.clear();

    d_idxs.push_back(0);
    for (string str: d_collect)
    {
        d_idxs.push_back(d_vocab.size());
        d_vocab.resize(d_vocab.size() + str.size() + 1);
        memcpy (&d_vocab[d_vocab.size() - str.size() - 1], &str[0], sizeof(char) * str.size());
    }   
    d_collect.clear();
}

void Vocab::saveBin(string const &path)
{
    ofstream ofs(path, ios::binary);
    if (!ofs.good())
    {
        cerr << "Could not write vocab: " << path << '\n';
        exit(1);
    }
    saveBin(&ofs);
    ofs.close();
}

void Vocab::saveBin(ofstream *ofs)
{
    uint64_t size;
    size = d_vocab.size();
    ofs->write(reinterpret_cast<char*>(&size), sizeof(uint64_t));
    ofs->write(&d_vocab[0], sizeof(char) * size);

    size = d_idxs.size();
    ofs->write(reinterpret_cast<char*>(&size), sizeof(uint64_t));
    ofs->write(reinterpret_cast<char*>(&d_idxs[0]), sizeof(uint32_t) * d_idxs.size());
}

void Vocab::addOrdered(string const &word)
{
    d_idxs.push_back(d_vocab.size());
    d_vocab.resize(d_vocab.size() + word.size() + 1);
    memcpy (&d_vocab[d_vocab.size() - word.size() -1], &word[0], sizeof(char) * word.size());
    d_vocab.back() = '\0';
}

void Vocab::loadOrdered(string const &path)
{
    ifstream in(path);
    if (!in.good())
    {
        cerr << "Could not read vocab: " << path << '\n';
        exit(1);
    }
    loadOrdered(&in);
}

void Vocab::loadOrdered(ifstream *ifs)
{
    string word;
    while(getline((*ifs), word))
        addOrdered(word);
}
