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
from rcn_py import topic_modeling
ps = PorterStemmer()



"""
This function queries ORCID by a full name and returns the corresponding ORCID ID if found. 
It uses the ORCID API to search for the name and retrieve the ORCID ID.
"""
def name_to_orcid_id(name):
    orcid_id = None

    headers = {
        "Accept": "application/vnd.orcid+json",
    }
    params = (("q", name),)
    
    response = requests.get(
        "https://pub.orcid.org/v3.0/search/", headers=headers, params=params
    )
    temp = response.json()

    # Check if any results were found
    if len(temp):
        orcid_id = temp["result"][0]["orcid-identifier"]["path"]
    return orcid_id


# Extract authors from a doc, and filter authors by country
def get_authors(doi):
    works = Works()
    metadata = works.doi(doi)

    orcid_list = []     # List to store ORCID IDs of authors
    author_names = []   # List to store names of authors
    
    if (metadata) and ("author" in metadata.keys()):
        authors = metadata["author"]

        for i in authors:
            if "ORCID" in i.keys():
                # Extract ORCID ID from the ORCID URL
                orcid_id_split = i["ORCID"].split("http://orcid.org/")[1]
                orcid_list.append(orcid_id_split)
            elif "given" in i.keys() and "family" in i.keys():
                # Retrieve ORCID ID based on author's name
                orcid_id_by_name = name_to_orcid_id(i["given"] + " " + i["family"])
                orcid_list.append(orcid_id_by_name)

            # Append author's name to the list
            author_names.append(i["given"] + " " + i["family"])
        return orcid_list, author_names
    else:
        return [], []


# Extract authors from a doc, and filter authors by country
# country_abb should be upper case, for example, 'NL'
def get_authors_one_country(doi, country_abb):
    works = Works()
    metadata = works.doi(doi)

    orcid_list = []   # List to store ORCID IDs of authors
    author_names = []  # List to store names of authors

    if (metadata) and ("author" in metadata.keys()):
        authors = metadata["author"]

        for i in authors:
            if "ORCID" in i.keys():
                # Extract ORCID ID from the ORCID URL
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
                # Retrieve ORCID ID based on author's name
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
            
            # Append author's name to the list
            author_names.append(i["given"] + " " + i["family"])
        return orcid_list, author_names
    else:
        return [], []


# query ORCID for an ORCID record
def query_orcid_for_record(orcid_id):

    # Send GET request to the ORCID API
    response = requests.get(
        url=requests.utils.requote_uri("https://pub.orcid.org/v3.0/" + orcid_id),
        headers={"Accept": "application/json"},
    )
    if response.ok:
        # If the response is successful, retrieve the JSON data
        response.raise_for_status()
        result = response.json()
        return result
    else:
        # If the response is not successful, return False
        return False


# query author name from ORCID
def from_orcid_to_name(orcid_id):
    # Query ORCID for the record
    orcid_record = query_orcid_for_record(orcid_id)
    # Extract the author's name from the ORCID record
    name_attr = orcid_record["person"]["name"]
    name = name_attr["given-names"]["value"] + " " + name_attr["family-name"]["value"]
    return name


# Extract works from ORCID
def extract_works_section(orcid_record):
    # Extract the "works" section from the ORCID record
    works = orcid_record["activities-summary"]["works"]["group"]
    return works


# Extract title and DOI
def extract_doi(work):
    # Extract the title from the work object
    work_summary = work["work-summary"][0]
    title = work_summary["title"]["title"]["value"]

    # Extract the DOI(s) from the work object
    dois = []
    if work_summary["external-ids"]:
        if "external-id" in work_summary["external-ids"].keys():
            for ws in work_summary["external-ids"]["external-id"]:
                if "external-id-type" in ws.keys() and "external-id-value" in ws.keys():
                    if ws["external-id-type"] == "doi":
                        dois.append(ws["external-id-value"])

   
    # If there is a DOI, extract the first one
    doi = dois[0] if dois else None
    doi = str(doi)
    return doi, title

"""
This function retrieves co-author information for a given full name using ORCID data. 
It performs various operations such as querying ORCID for the author's ORCID ID, 
extracting works information, conducting LDA topic modeling, 
and filtering authors based on certain criteria.
"""
def orcid_get_coauthors(full_name):
    # Retrieve the ORCID ID for the given full name
    orcid_id = name_to_orcid_id(full_name)
    # Query the ORCID API for the author's record
    orcid_record = query_orcid_for_record(orcid_id)
    # Extract the works section from the ORCID record
    docs = extract_works_section(orcid_record)

    # Initialize lists to store co-author information
    all_orcid = []
    all_names = []
    all_group = []
    all_topic = []
    coauthor_links = []

    # LDA topic modeling
    doi_list = []
    for doc in docs:
        # Extract DOI and title from each work
        doi, title = extract_doi(doc)
        doi_list.append(doi)

    # Perform LDA topic modeling and clustering
    cluster_dict, idx2topics = orcid_lda_cluster(doi_list)

    for doc in docs:
        # Extract DOI and title from each work
        doi, title = extract_doi(doc)
        # Extract DOI and title from each work
        doc_group = cluster_dict[doi]

        # Extract DOI and title from each work
        orcid_list, name_list = get_authors(doi)
        
        # Apply filters and store filtered co-author information
        filtered_orcid_list = []
        filtered_name_list = []
        author_group_list = []
        author_topics = []
        for i in range(len(orcid_list)):
            # Additional filtering criteria can be applied here
            # orcid_record = query_orcid_for_record(orcid_list[i])
            # country = orcid_record['person']['addresses']['address'][0]['country']['value']
            # if country == 'NL':
            filtered_orcid_list.append(orcid_list[i])
            filtered_name_list.append(name_list[i])
            author_group_list.append(doc_group)
            author_topics.append(idx2topics[doc_group])

        # Generate co-author links by combining filtered ORCID IDs
        if len(filtered_orcid_list) >= 2:
            coauthor_links = coauthor_links + list(combinations(filtered_orcid_list, 2))

        # Store co-author information in lists
        all_orcid += filtered_orcid_list
        all_names += filtered_name_list
        all_group += author_group_list
        all_topic += author_topics

    # Assign new group numbers based on unique groups
    group_temp = []
    new_group_num = []
    for g in all_group:
        if g not in group_temp:
            group_temp.append(g)
        new_group_num.append(group_temp.index(g))

    # Create a DataFrame to store co-author information
    df = pd.DataFrame()
    df["orcid"] = all_orcid
    df["name"] = all_names
    df["group"] = new_group_num
    df["topics"] = all_topic

    # Remove duplicate ORCID IDs and keep the first occurrence
    new_df = df.drop_duplicates(subset=["orcid"], keep="first", ignore_index=True)

    return new_df, coauthor_links


def orcid_lda_cluster(dois):
    cleaned_abs_corpus = [] # Cleaned abstract corpus
    clusters = {}           # Dictionary to store cluster assignments for each DOI
    works = Works()

    # Iterate over DOIs
    for i in dois:
        w = works.doi(i)
        if "abstract" in w.keys():
            cleaned_abs_corpus.append(topic_modeling.preprocess(w["abstract"]))
        elif "title" in w.keys() and w["title"]:
            cleaned_abs_corpus.append(topic_modeling.preprocess(w["title"][0]))
        else:
            cleaned_abs_corpus.append([])

    # Create dictionary and corpus for LDA model
    dictionary = gensim.corpora.Dictionary(cleaned_abs_corpus)
    corpus = [dictionary.doc2bow(text) for text in cleaned_abs_corpus]

    # Apply LDA topic modeling
    lda_model = gensim.models.LdaMulticore(
        corpus, num_topics=8, id2word=dictionary, passes=10, workers=2
    )

    idx2topics = {}
    for idx, topic in lda_model.print_topics(-1):
        idx2topics[idx] = topic

    # Assign clusters based on topic scores
    for i in range(len(cleaned_abs_corpus)):
        scores = []
        topics = []
        for j1, j2 in lda_model[corpus[i]]:
            topics.append(j1)
            scores.append(j2)
            clusters[dois[i]] = scores.index(max(scores))

    return clusters, idx2topics

# Network visualization using Pyvis
def orcid_network(name, author_df, link):
    # Initialize variables for network construction
    sources = []
    targets = []
    weights = []

    # Extract source, target, and weight information from links
    for i in link:
        sources.append(i[0])
        targets.append(i[1])
        weights.append(link.count(i))

    # Create dictionaries to map ORCID ID to name and group
    id2name = {}
    id2group = {}
    for index in range(author_df.shape[0]):
        id2name[author_df["orcid"][index]] = author_df["name"][index]
        id2group[author_df["orcid"][index]] = int(author_df["group"][index])

    # Create the network visualization using Pyvis
    N = Network(height=800, width="100%", bgcolor="#222222", font_color="white")
    N.toggle_hide_edges_on_drag(False)
    N.barnes_hut()

    # Add nodes and edges to the network
    edge_data = zip(sources, targets, weights)
    for e in edge_data:
        src = e[0]
        dst = e[1]
        w = e[2]

        N.add_node(src, src, title=src, group=id2group[src])
        N.add_node(dst, dst, title=dst, group=id2group[dst])
        N.add_edge(src, dst, value=w)

    # Update node labels and hover data
    for node in N.nodes:
        node["title"] = node["id"]
        node["label"] = id2name[node["id"]]

    # Save the network visualization as an HTML file
    N.show(name + ".html")
