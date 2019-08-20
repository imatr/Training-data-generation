#include "w2v.h"

#include <vector>
#include <fstream>
#include <stdio.h>
#include <math.h>
#include <malloc.h>
#include <iostream>
#include <string.h>
#include <unordered_map>

using namespace std;

w2v::w2v()
//:
{
}

w2v::w2v(string const &path)
//:
{
    load(path);
}

void w2v::printVocab()
{
    for (int beg = 0; beg != words; ++beg)
        cout << beg << ".\t" << &vocab[beg * max_w] << '\n';
}

bool w2v::find(char const *src, std::string *bestw2, float *bestd2)
{
    for (a = 0; a < top_n; a++) bestd[a] = 0;
    for (a = 0; a < top_n; a++) bestw[a] = 0;
    strcpy(st1, src);
    cn = 0;
    b = 0;
    c = 0;
    while (1) {
        st[cn][b] = st1[c];
        b++;
        c++;
        st[cn][b] = 0;
        if (st1[c] == 0) break;
        if (st1[c] == ' ') {
            cn++;
            b = 0;
            c++;
        }
    }
    cn++;
    for (a = 0; a < cn; a++) {
        for (b = 0; b < words; b++) if (!strcmp(&vocab[b * max_w], st[a])) break;
        if (b == words) b = -1;
        bi[a] = b;
        //printf("\nWord: %s  Position in vocabulary: %lld\n", st[a], bi[a]);
        if (b == -1) {
            //printf("Out of dictionary word!\n");
            return false;
        }
    }
    //if (b == -1) continue;
    //printf("\n                                              Word       Cosine distance\n------------------------------------------------------------------------\n");
    for (a = 0; a < size; a++) vec[a] = 0;
    for (b = 0; b < cn; b++) {
        if (bi[b] == -1) continue;
        for (a = 0; a < size; a++) vec[a] += M[a + bi[b] * size];    
    }
    len = 0;
    for (a = 0; a < size; a++) len += vec[a] * vec[a];
    len = sqrt(len);
    for (a = 0; a < size; a++) vec[a] /= len;
    for (a = 0; a < top_n; a++) bestd[a] = -1;
    for (a = 0; a < top_n; a++) bestw[a] = 0;
    for (c = 0; c < words; c++) {
        a = 0;
        for (b = 0; b < cn; b++) if (bi[b] == c) a = 1;
        if (a == 1) continue;
        dist = 0;
        for (a = 0; a < size; a++) dist += vec[a] * M[a + c * size];
        for (a = 0; a < top_n; a++) {
            if (dist > bestd[a]) {
                for (d = top_n - 1; d > a; d--) 
                {
                    bestw[d] = bestw[d-1];
                    bestd[d] = bestd[d - 1];
                }
                bestd[a] = dist;
                bestw[a] = c;
                break;
            }
        }
    }
    for (a =0; a!= top_n; a++)
    {
        bestw2[a] = string(&vocab[bestw[a] * max_w]);
        bestd2[a] = bestd[a];
    }
    return true;
}

int w2v::load(std::string const &loc) {
    cerr << "Loading: " << loc << '\n';
    FILE *f;
    strcpy(file_name, loc.c_str());
    f = fopen(file_name, "rb");
    if (f == NULL) {
        printf("Input file not found\n");
        return -1;
    }
    (void)(fscanf(f, "%lld", &words) + 1);
    (void)(fscanf(f, "%lld", &size) + 1);
    vocab = (char *)malloc((long long)words * max_w * sizeof(char));
    M = (float *)malloc((long long)words * (long long)size * sizeof(float));
    if (M == NULL) {
        printf("Cannot allocate memory: %lld MB    %lld  %lld\n", (long long)words * size * sizeof(float) / 1048576, words, size);
        return -1;
    }
    for (b = 0; b < words; b++) {
        a = 0;
        while (1) {
            vocab[b * max_w + a] = fgetc(f);
            if (feof(f) || (vocab[b * max_w + a] == ' ')) break;
            if ((a < max_w) && (vocab[b * max_w + a] != '\n')) a++;
        }
        vocab[b * max_w + a] = 0;
        for (a = 0; a < size; a++) (void)(fread(&M[a + b * size], sizeof(float), 1, f) + 1);
        len = 0;
        for (a = 0; a < size; a++) len += M[a + b * size] * M[a + b * size];
        len = sqrt(len);
        for (a = 0; a < size; a++) M[a + b * size] /= len;
    }
    fclose(f);

    // Make it much faster to find a word
    for (b = 0; b < words; b++)
    {
        string word = string(&vocab[b * max_w]);
        d_myVocab.addWord(word);
    }
    d_myVocab.optimize();
    d_vocabLink = vector<int>(words+2);
    for (b = 0; b < words; b++)
    {
        string word = string(&vocab[b * max_w]);
        d_vocabLink[d_myVocab.getId(word)] = b;
    }
    return 0;
}

int w2v::getId(string const &word)
{
    int ret = 0;
    int id = d_myVocab.getId(word);
    if (id != 0)
        ret = d_vocabLink[id];
    return ret;
}

double w2v::distance(string const &word1, string const &word2)
{
    int idx1 = getId(word1);
    if (idx1 == 0)
        return 0.0;
    int idx2 = getId(word2);
    if (idx2 == 0)
        return 0.0;
    dist = 0;
    for (a = 0; a < size; a++) {
        dist += M[a + idx1 * size] * M[a + idx2 * size];
    }
    return dist;
}
