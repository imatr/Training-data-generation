#include "embeds.h"

#include <iostream>
#include <map>
#include <sstream>
#include <string>
#include <vector>

using namespace std;

extern "C" {
    Embeds* Embeds_create() {
        return new Embeds();
    }
    void Embeds_loadTxt(Embeds* embeddings, char* filename) {
        embeddings->loadTxt(filename);
    }
    void Embeds_loadBin(Embeds* embeddings, char* filename) {
        embeddings->loadBin(filename);
    }
    void Embeds_saveTxt(Embeds* embeddings, char* filename) {
        embeddings->saveTxt(filename);
    }
    void Embeds_saveBin(Embeds* embeddings, char* filename) {
        embeddings->saveBin(filename);
    }
    const char* Embeds_find(Embeds* embeddings, const char* word) {
        vector<string> candidates(40);
        vector<double> similarities(40);
        embeddings->find(word, &candidates[0], &similarities[0]);
        static string results = "";
        results.clear();
        for (int i=0; i<candidates.size(); i++) {
            results.append(candidates[i]);
            if (i < candidates.size()-1) results.append(",");
        }
        return results.c_str();
    }
}

Embeds::Embeds()
//:
{
}

Embeds::Embeds(string const &vec, string const &cache, bool bin)
:
    d_cachePath(cache),
    d_rawW2V(vec)
{
    if (d_cachePath == "")
        d_cachePath = std::string(vec) + ".cache";
    if (bin)
        loadBin(d_cachePath);
    else
        loadTxt(vec);
}

void Embeds::loadTxt(string const &path)
{
    ifstream ifs(path);
    if (!ifs.good())
    {
        cerr << "Could not read w2v model: " << path << '\n';
        exit(1);
    }

    ifs >> d_numCands;
    ifs >> d_numWords; 
    cout << d_numCands << '\t' << d_numWords << '\n';
    d_cands = vector<uint32_t>(d_numCands * d_numWords);
    d_vals = vector<double>(d_numCands * d_numWords);
    
    vector<string> idToWord = vector<string>(d_numWords + 1);
    string word;
    uint32_t id;
    double dist;
    for (int beg = 0; beg != d_numWords ; ++beg)
    {
        ifs >> word;
        idToWord[beg+1] = word;
        d_vocab.addWord(word);
    }
    d_vocab.optimize();
    getline(ifs, word);
    for (int beg = 0; beg != d_numWords; ++beg)
    {
        ifs >> id;
        size_t newId = d_vocab.getId(idToWord[id]);
        for (int candIdx = 0; candIdx != d_numCands; ++candIdx)
        {
            ifs >> id >> dist;
            d_cands[newId * d_numCands + candIdx] = d_vocab.getId(idToWord[id]);
            d_vals[newId * d_numCands + candIdx] = dist;
        }
    }
    cout << "read all\n"; 
}

void Embeds::loadBin(string const &loc)
{
    cerr << "Loading: " << loc << '\n';
    ifstream ifs(loc, ios::binary);
    if (!ifs.good())
    {
        cerr << "No cache found, creating one at: " << loc << '\n';
        d_numCands = 40;
        d_numWords = d_rawW2V.getWords();
        d_cands = vector<uint32_t>(d_numWords * d_numCands);
        d_vals = vector<double>(d_numWords * d_numCands);
        char *vocab = d_rawW2V.getVocab();
        for (int beg = 0; beg != d_numWords; ++beg)
            d_vocab.addWord(string(&vocab[beg * 50]));
        d_vocab.optimize();
        return;
    }
    d_vocab.loadBin(&ifs);
    ifs.read(reinterpret_cast<char*>(&d_numCands), sizeof(uint64_t));
    ifs.read(reinterpret_cast<char*>(&d_numWords), sizeof(uint64_t));
    d_numCands = 40;
    
    d_cands = vector<uint32_t>((d_numWords +1) * d_numCands);
    ifs.read(reinterpret_cast<char*>(&d_cands[0]), sizeof(uint32_t) * (d_numWords + 1) * d_numCands);
    d_vals = vector<double>((d_numWords +1)* d_numCands);
    ifs.read(reinterpret_cast<char*>(&d_vals[0]), sizeof(double) * (d_numWords + 1 )* d_numCands);
    ifs.close();

}

void Embeds::saveBin(string const &path)
{
    cerr << "Saving: " << path << '\n';
    ofstream ofs(path);
    if (!ofs.good())
    {
        cerr << "Could not write w2v model: " << path << '\n';
        exit(1);
    }
    d_vocab.saveBin(&ofs);
    ofs.write(reinterpret_cast<char*>(&d_numCands), sizeof(uint64_t));
    ofs.write(reinterpret_cast<char*>(&d_numWords), sizeof(uint64_t));

    ofs.write(reinterpret_cast<char*>(&d_cands[0]), sizeof(uint32_t) * d_numCands * (d_numWords + 1));
    ofs.write(reinterpret_cast<char*>(&d_vals[0]), sizeof(double) * d_numCands * (d_numWords + 1));
    ofs.close();

    
}

void Embeds::saveTxt(string const &path)
{
    cerr << "Saving: " << path << '\n';
    ofstream ofs(path);
    if (!ofs.good())
    {
        cerr << "Could not write w2v model: " << path << '\n';
        exit(1);
    }
    ofs << d_numCands << '\n'
        << d_numWords << '\n';
    d_vocab.save(&ofs);
    
    for (int wordId = 1; wordId != d_numWords + 1; ++wordId)
    {
        ofs << wordId << '\t';
        for (int candIdx = 0; candIdx != d_numCands; ++candIdx)
            ofs << d_cands[wordId * d_numCands + candIdx] << '\t' 
                << d_vals[wordId * d_numCands + candIdx] << '\t';
        ofs << '\n';
    }
    ofs.close();
}

bool Embeds::find(char const *word, string *retCands, double *retVals)
{
    uint32_t wordId = d_vocab.getId(word);
    if(wordId == 0)
        return false;

    //cout << wordId <<  '\n';
    if (d_cands[wordId * d_numCands] == 0)
    {
        //cerr << "word " << word << " not found!\n";
        vector<string> cands(40);
        vector<float> vals(40);
        bool have = d_rawW2V.find(word, &cands[0], &vals[0]);
        if (!have) //This should never happen?
            return false;
        for (size_t a = 0; a != 40; ++a)
        {
            d_cands[wordId * d_numCands + a] = d_vocab.getId(cands[a]);
            retCands[a] = cands[a];
            d_vals[wordId * d_numCands + a] = double(vals[a]);
            retVals[a] = vals[a];
        }
        d_cachedSomething = true;
    }
    else
    {
        //cout << "Found " << word << '\n';
        for (size_t a = 0; a != 40; ++a)
        {
            retCands[a] = d_vocab.getWord(d_cands[wordId * d_numCands + a]);
            retVals[a] = d_vals[wordId * d_numCands + a];
        }
    }
    return true;
}
