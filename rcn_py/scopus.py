from pybliometrics.scopus import AuthorSearch
from pybliometrics.scopus import AuthorRetrieval
import numpy as np
import pandas as pd
import itertools
from pyvis.network import Network
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize
import gensim
from gensim import corpora
import time
import nltk
import re
from nltk.corpus import stopwords

ps = PorterStemmer()
nltk.download("stopwords")
stop_words = set(stopwords.words("english"))



def get_hindex(au_id):
    au = AuthorRetrieval(au_id)
    return au.h_index



def clean_text(text):
    text = text.replace('\n'," ") 
    text = re.sub(r"-", " ", text) 
    text = re.sub(r"\d+/\d+/\d+", "", text) 
    text = re.sub(r"[0-2]?[0-9]:[0-6][0-9]", "", text) 
    text = re.sub(r"[\w]+@[\.\w]+", "", text) 
    text = re.sub(r"/[a-zA-Z]*[:\//\]*[A-Za-z0-9\-_]+\.+[A-Za-z0-9\.\/%&=\?\-_]+/i", "", text)
    pure_text = ''
    for letter in text:
        # Leave only letters and spaces
        if letter.isalpha() or letter==' ':
            letter = letter.lower()
            pure_text += letter
            
    corpus_lst = [ps.stem(word) for word in pure_text.split() if word not in stop_words]
    return corpus_lst



def lda_cluster(docs):
    cleaned_abs_corpus = []
    for i in range(len(docs)):
        if docs.description[i]:
            cleaned_abs_corpus.append(clean_text(docs.description[i]))
        else:
            cleaned_abs_corpus.append(clean_text(docs.title[i]))

    num_topics = 4
    dictionary = corpora.Dictionary(cleaned_abs_corpus) 
    corpus = [dictionary.doc2bow(text) for text in cleaned_abs_corpus]

    t0= time.time()
    passes= 150
    np.random.seed(1)

    lda_model = gensim.models.LdaMulticore(corpus=corpus,
                                           id2word=dictionary,
                                           num_topics=num_topics,
                                           chunksize= 4000, 
                                           batch= True,
                                           minimum_probability=0.001,
                                           iterations=350,
                                           passes=passes)
    group = []
    for i in range(len(cleaned_abs_corpus)):
        scores = []
        for j1,j2 in lda_model[corpus[i]]:
            scores.append(j2)
        group.append(scores.index(max(scores)))
    docs['group'] = group
    return docs



def nld_coauthor(author_id, depth, width, node_retrieved):
    au = AuthorRetrieval(author_id)
    docs = pd.DataFrame(au.get_documents())
    # Get clusters of docs
    docs = lda_cluster(docs)
    # Access to documents for the last five years
    # new_docs = docs[(docs.coverDate > '2018')]
    au_id = docs.author_ids
    
    link = []
    all_node = []
    groups = []
    au_group = {}

    node_retrieved.append(author_id)
    
    for i in range(len(au_id)):
        coau_id = au_id[i].split(";")
        coau_id = list(map(int, coau_id))
        new_coau_id = []
        for j in coau_id[:int(width)]:
            aff = AuthorRetrieval(j).affiliation_current
            if aff:
                # Geo-filtering 
                # todo: all the affiliations 
                # if AuthorRetrieval(j).affiliation_current[0][7] == 'nld':   
                    if j not in all_node:
                        all_node.append(j)
                    if docs.group[i] not in groups:
                        groups.append(docs.group[i])
                    new_coau_id.append(j)
                    au_group[j] = groups.index(docs.group[i])
                    
        sorted_new_coauid = list(map(int, new_coau_id))
        sorted_new_coauid.sort()
        link = link+list(itertools.combinations(sorted_new_coauid, 2))
        # Do recursion (increase depth of the network)
        if depth > 0:
            for j in sorted_new_coauid[:int(width)]:
                if j not in node_retrieved:
                    nld_coauthor(j, depth-1, width, node_retrieved)
    return all_node, link, au_group



def get_coauthor(author_first, author_last, depth, width):
    s = AuthorSearch('AUTHLAST('+author_last+') and AUTHFIRST('+author_first+')')
    author_id = s.authors[0].eid.split('-')[-1]
    
    node_retrieved = []
    node, link, au_group = nld_coauthor(author_id, depth, width, node_retrieved)
    sources = []
    targets = []
    weights = []

    for i in link:
        sources.append(i[0])
        targets.append(i[1])
        weights.append(link.count(i))
    
    # Pyvis network
    N = Network(height=800, width="100%", bgcolor="#222222", font_color="white")
    N.toggle_hide_edges_on_drag(False)
    N.barnes_hut()

    edge_data = zip(sources, targets, weights)

    for e in edge_data:
        src = e[0]
        dst = e[1]
        w = e[2]

        N.add_node(src, src, title=src, group = au_group[src])
        N.add_node(dst, dst, title=dst, group = au_group[dst])
        N.add_edge(src, dst, value=w)

    neighbor_map = N.get_adj_list()

    # add neighbor data to node hover data
    for node in N.nodes:
        neighbors = []
        for neighbor_id in neighbor_map[node["id"]]:
            neigh = AuthorRetrieval(neighbor_id)
            neighbors.append(neigh.given_name+' '+neigh.surname)
        #node["title"] = " Neighbors: \n" + " \n".join(neighbors)
        node["title"] = "Link to the author’s API page:\n" + AuthorRetrieval(node["id"]).self_link
        node["value"] = get_hindex(node["id"])
        node["label"] = AuthorRetrieval(node["id"]).given_name+' '+AuthorRetrieval(node["id"]).surname

    N.show(author_last + ".html")