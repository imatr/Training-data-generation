#ifndef INCLUDED_W2V_
#define INCLUDED_W2V_

#include <string>
#include <stdint.h>
#include <vector>
#include <unordered_map>
#include <utility>
#include "./vocab.h"

class w2v
{
    static int const top_n = 40;
    long long max_w = 50;
    char st1[2000];
    char file_name[2000], st[100][2000];
    int bestw[top_n];
    float dist, len, bestd[top_n], vec[2000];
    long long words, size, a, b, c, d, cn, bi[100];
    float *M;
    char *vocab;
    long long max_size = 2000;
    Vocab d_myVocab;
    std::vector<int> d_vocabLink;

    public:
        w2v();
        w2v(std::string const &path);

        int load(std::string const &path);

        bool find(char const *word, std::string *bestw2, float *bestd2);
        double distance(std::string const &word1, std::string const &word2);
        int getId(std::string const &word);
    
        void printVocab();
        long long getWords(){return words;};
        char * getVocab(){return vocab;};
    private:
};
        
#endif
