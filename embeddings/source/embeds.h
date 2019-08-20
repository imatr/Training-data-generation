#ifndef INCLUDED_EMBEDS_
#define INCLUDED_EMBEDS_

#include <string>
#include <stdint.h>
#include "./w2v.h"

class Embeds
{
    std::string d_cachePath;
    w2v d_rawW2V;
    int d_numWords;
    int d_numCands;
    bool d_cachedSomething = false;

    Vocab d_vocab;
    std::vector<uint32_t> d_cands;
    std::vector<double> d_vals;

    public:
        Embeds();
        Embeds(std::string const &vec, std::string const &cache = "", bool bin = true);
        
        void loadBin(std::string const &path);
        void loadTxt(std::string const &path);
        void saveBin(std::string const &path);
        void saveTxt(std::string const &path);
        void combine(int argc, char* argv[]);

        bool find(char const *word, std::string *retCands, double *retVals);
        double getDistance(std::string const &word1, std::string const &word2);

    private:
};
        
#endif
