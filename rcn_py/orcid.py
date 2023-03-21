import re
from itertools import combinations

import gensim
import nltk
import pandas as pd
import requests
from crossref.restful import Works
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer, WordNetLemmatizer
from pyvis.network import Network

nltk.download("omw-1.4")
nltk.download("stopwords")
nltk.download("wordnet")
stop_words = set(stopwords.words("english"))
wnl = WordNetLemmatizer()
ps = PorterStemmer()



# Query ORCID by a fullname
headers = {
    "Accept": "application/vnd.orcid+json",
}


def name_to_orcid_id(name):
    orcid_id = None

    params = (("q", name),)
    response = requests.get(
        "https://pub.orcid.org/v3.0/search/", headers=headers, params=params
    )
    temp = response.json()
    if len(temp):
        orcid_id = temp["result"][0]["orcid-identifier"]["path"]
    return orcid_id


# Extract authors from a doc, and filter authors by country
def get_authors(doi):
    works = Works()
    metadata = works.doi(doi)
    # It's possible that the acquired
    if (metadata) and ("author" in metadata.keys()):
        authors = metadata["author"]
        orcid_list = []
        author_names = []

        for i in authors:
            if "ORCID" in i.keys():
                orcid_id_split = i["ORCID"].split("http://orcid.org/")[1]
                orcid_list.append(orcid_id_split)
            elif "given" in i.keys() and "family" in i.keys():
                orcid_id_by_name = name_to_orcid_id(i["given"] + " " + i["family"])
                orcid_list.append(orcid_id_by_name)
            else:
                continue
            author_names.append(i["given"] + " " + i["family"])
        return orcid_list, author_names
    else:
        return [], []


# Extract authors from a doc, and filter authors by country
# country_abb should be upper case, for example, 'NL'
def get_authors_one_country(doi, country_abb):
    works = Works()
    metadata = works.doi(doi)
    # It's possible that the acquired
    if (metadata) and ("author" in metadata.keys()):
        authors = metadata["author"]
        orcid_list = []
        author_names = []

        for i in authors:
            if "ORCID" in i.keys():
                orcid_id_split = i["ORCID"].split("http://orcid.org/")[1]
                orcid_record = query_orcid_for_record(orcid_id_split)
                if orcid_record["person"]["addresses"]["address"]:
                    country = orcid_record["person"]["addresses"]["address"][0][
                        "country"
                    ]["value"]
                else:
                    country = ""
                if country == country_abb:
                    orcid_list.append(orcid_id_split)
            elif "given" in i.keys() and "family" in i.keys():
                orcid_id_by_name = name_to_orcid_id(i["given"] + " " + i["family"])
                orcid_record = query_orcid_for_record(orcid_id_by_name)
                if orcid_record["person"]["addresses"]["address"]:
                    country = orcid_record["person"]["addresses"]["address"][0][
                        "country"
                    ]["value"]
                else:
                    country = ""
                if country == country_abb:
                    orcid_list.append(orcid_id_by_name)
            else:
                continue
            author_names.append(i["given"] + " " + i["family"])
        return orcid_list, author_names
    else:
        return [], []


# URL for ORCID API
ORCID_RECORD_API = "https://pub.orcid.org/v3.0/"


# query ORCID for an ORCID record
def query_orcid_for_record(orcid_id):
    response = requests.get(
        url=requests.utils.requote_uri(ORCID_RECORD_API + orcid_id),
        headers={"Accept": "application/json"},
    )
    if response.ok:
        response.raise_for_status()
        result = response.json()
        return result
    else:
        return False


# query author name from ORCID
def from_orcid_to_name(orcid_id):
    orcid_record = query_orcid_for_record(orcid_id)
    name_attr = orcid_record["person"]["name"]
    name = name_attr["given-names"]["value"] + " " + name_attr["family-name"]["value"]
    return name


# Extract works from ORCID
def extract_works_section(orcid_record):
    works = orcid_record["activities-summary"]["works"]["group"]
    return works


# Extract title and DOI
def extract_doi(work):
    work_summary = work["work-summary"][0]
    title = work_summary["title"]["title"]["value"]

    dois = []
    if work_summary["external-ids"]:
        if "external-id" in work_summary["external-ids"].keys():
            for ws in work_summary["external-ids"]["external-id"]:
                if "external-id-type" in ws.keys() and "external-id-value" in ws.keys():
                    if ws["external-id-type"] == "doi":
                        dois.append(ws["external-id-value"])

   
    # if there is a DOI, we can extract the first one
    doi = dois[0] if dois else None
    doi = str(doi)
    return doi, title


def orcid_get_coauthors(full_name):
    orcid_id = name_to_orcid_id(full_name)
    orcid_record = query_orcid_for_record(orcid_id)
    docs = extract_works_section(orcid_record)

    all_orcid = []
    all_names = []
    all_group = []
    all_topic = []
    coauthor_links = []

    # LDA topic modeling
    doi_list = []
    for doc in docs:
        doi, title = extract_doi(doc)
        doi_list.append(doi)
    cluster_dict, idx2topics = orcid_lda_cluster(doi_list)

    for doc in docs:
        doi, title = extract_doi(doc)
        doc_group = cluster_dict[doi]
        orcid_list, name_list = get_authors(doi)
        # Geo-filtering
        filtered_orcid_list = []
        filtered_name_list = []
        author_group_list = []
        author_topics = []
        for i in range(len(orcid_list)):
            # orcid_record = orcid.query_orcid_for_record(orcid_list[i])
            # if orcid_record['person']['addresses']['address']:
            #     country = orcid_record['person']['addresses']['address'][0]['country']['value']
            # else:
            #     country = ''
            # if country == 'NL':
            filtered_orcid_list.append(orcid_list[i])
            filtered_name_list.append(name_list[i])
            author_group_list.append(doc_group)
            author_topics.append(idx2topics[doc_group])

        # Combination
        if len(filtered_orcid_list) >= 2:
            coauthor_links = coauthor_links + list(combinations(filtered_orcid_list, 2))

        all_orcid += filtered_orcid_list
        all_names += filtered_name_list
        all_group += author_group_list
        all_topic += author_topics

    group_temp = []
    new_group_num = []
    for g in all_group:
        if g not in group_temp:
            group_temp.append(g)
        new_group_num.append(group_temp.index(g))

    df = pd.DataFrame()
    df["orcid"] = all_orcid
    df["name"] = all_names
    df["group"] = new_group_num
    df["topics"] = all_topic

    new_df = df.drop_duplicates(subset=["orcid"], keep="first", ignore_index=True)

    return new_df, coauthor_links


def clean_text(text):
    text = text.replace("\n", " ")
    text = re.sub(r"-", " ", text)
    text = re.sub(r"\d+/\d+/\d+", "", text)
    text = re.sub(r"[0-2]?[0-9]:[0-6][0-9]", "", text)
    text = re.sub(r"[\w]+@[\.\w]+", "", text)
    text = re.sub(
        r"/[a-zA-Z]*[:\//\]*[A-Za-z0-9\-_]+\.+[A-Za-z0-9\.\/%&=\?\-_]+/i", "", text
    )
    pure_text = ""
    for letter in text:
        # Leave only letters and spaces
        if letter.isalpha() or letter == " ":
            letter = letter.lower()
            pure_text += letter

    corpus_lst = [ps.stem(word) for word in pure_text.split() if word not in stop_words]
    return corpus_lst


def lemmatize_stemming(text):
    return ps.stem(WordNetLemmatizer().lemmatize(text, pos="v"))


# Tokenize and lemmatize
def preprocess(text):
    result = []
    for token in gensim.utils.simple_preprocess(text):
        if token not in gensim.parsing.preprocessing.STOPWORDS and len(token) > 3:
            result.append(lemmatize_stemming(token))

    return result


def orcid_lda_cluster(dois):
    cleaned_abs_corpus = []
    clusters = {}
    works = Works()
    for i in dois:
        w = works.doi(i)
        if "abstract" in w.keys():
            cleaned_abs_corpus.append(preprocess(w["abstract"]))
        elif "title" in w.keys() and w["title"]:
            cleaned_abs_corpus.append(preprocess(w["title"][0]))
        else:
            cleaned_abs_corpus.append([])

    dictionary = gensim.corpora.Dictionary(cleaned_abs_corpus)
    corpus = [dictionary.doc2bow(text) for text in cleaned_abs_corpus]

    # np.random.seed(1)

    # lda_model = gensim.models.LdaMulticore(corpus=corpus,
    #                                        id2word=dictionary,
    #                                        num_topics=num_topics,
    #                                        chunksize= 4000,
    #                                        batch= True,
    #                                        minimum_probability=0.001,
    #                                        iterations=350,
    #                                        passes=passes)

    lda_model = gensim.models.LdaMulticore(
        corpus, num_topics=8, id2word=dictionary, passes=10, workers=2
    )

    idx2topics = {}
    for idx, topic in lda_model.print_topics(-1):
        idx2topics[idx] = topic

    for i in range(len(cleaned_abs_corpus)):
        scores = []
        topics = []
        for j1, j2 in lda_model[corpus[i]]:
            topics.append(j1)
            scores.append(j2)
            clusters[dois[i]] = scores.index(max(scores))

    return clusters, idx2topics


def orcid_network(name, author_df, link):
    sources = []
    targets = []
    weights = []

    for i in link:
        sources.append(i[0])
        targets.append(i[1])
        weights.append(link.count(i))

    id2name = {}
    id2group = {}
    for index in range(author_df.shape[0]):
        id2name[author_df["orcid"][index]] = author_df["name"][index]
        id2group[author_df["orcid"][index]] = int(author_df["group"][index])

    # Pyvis network
    N = Network(height=800, width="100%", bgcolor="#222222", font_color="white")
    N.toggle_hide_edges_on_drag(False)
    N.barnes_hut()

    edge_data = zip(sources, targets, weights)

    for e in edge_data:
        src = e[0]
        dst = e[1]
        w = e[2]

        N.add_node(src, src, title=src, group=id2group[src])
        N.add_node(dst, dst, title=dst, group=id2group[dst])
        N.add_edge(src, dst, value=w)

    # add neighbor data to node hover data
    for node in N.nodes:
        node["title"] = node["id"]
        node["label"] = id2name[node["id"]]

    N.show(name + ".html")
