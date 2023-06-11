import itertools

import networkx as nx
import pandas as pd
from crossref.restful import Works
from pyvis.network import Network
from scholarly import scholarly

from rcn_py import orcid


def scholar_author_info(fullname):
    # Search author info by their name
    search_query_author = scholarly.search_author(fullname)
    author = scholarly.fill(next(search_query_author))
    # Get all the publication info of the author
    docs = []
    for i in range(len(author["publications"])):
        docs.append(author["publications"][i]["bib"])

    title = []
    coauthor_name = []
    abstract = []

    pub_df = pd.DataFrame()
    for doc in docs:
        try:
            search_pub = scholarly.search_pubs(doc["title"])
            pub_info = next(search_pub)
            title.append(pub_info["bib"]["title"])
            coauthor_name.append(pub_info["bib"]["author"])
            abstract.append(pub_info["bib"]["abstract"])
        except:
            continue
    pub_df["title"] = title
    pub_df["authors"] = coauthor_name
    pub_df["abstarct"] = abstract

    # pub_df.to_csv(folderpath + "/" + fullname + "_scholar.csv")
    return pub_df


def crossref_author_by_orcid(orcid_id):
    # Extract author info using ORCID
    orcid_record = orcid.query_orcid_for_record(orcid_id)
    if orcid_record is False:
        return
    docs = orcid.extract_works_section(orcid_record)

    # Extarct publication info from Crossref
    title_list = []
    doi_list = []
    coauthor_name = []
    coauthor_orcid = []
    abstract = []
    works = Works()
    for doc in docs:
        doi, title = orcid.extract_doi(doc)
        w = works.doi(doi)
        orcid_list, name_list = orcid.get_authors(doi)

        title_list.append(title)
        doi_list.append(doi)
        if w:
            if "abstract" in w.keys():
                abstract.append(w["abstract"])
            else:
                abstract.append("")
        else:
            abstract.append("")
        coauthor_name.append(name_list)
        coauthor_orcid.append(orcid_list)

    pub_df = pd.DataFrame()
    pub_df["title"] = title_list
    pub_df["doi"] = doi_list
    pub_df["authors"] = coauthor_name
    pub_df["abstarct"] = abstract
    pub_df["author_orcid"] = coauthor_orcid

    return pub_df


# Store all publication info of one person
def crossref_author_by_name(fullname):
    # Extract author info using ORCID
    orcid_id = orcid.name_to_orcid_id(fullname)
    orcid_record = orcid.query_orcid_for_record(orcid_id)
    if orcid_record is False:
        return
    docs = orcid.extract_works_section(orcid_record)

    # Extarct publication info from Crossref
    title_list = []
    doi_list = []
    coauthor_name = []
    coauthor_orcid = []
    abstract = []
    works = Works()
    for doc in docs:
        doi, title = orcid.extract_doi(doc)
        w = works.doi(doi)
        orcid_list, name_list = orcid.get_authors(doi)

        title_list.append(title)
        doi_list.append(doi)
        if w:
            if "abstract" in w.keys():
                abstract.append(w["abstract"])
            else:
                abstract.append("")
        else:
            abstract.append("")
        coauthor_name.append(name_list)
        coauthor_orcid.append(orcid_list)

    pub_df = pd.DataFrame()
    pub_df["title"] = title_list
    pub_df["doi"] = doi_list
    pub_df["authors"] = coauthor_name
    pub_df["abstarct"] = abstract
    pub_df["author_orcid"] = coauthor_orcid

    # pub_df.to_csv(folderpath + "/" + fullname + "_crossref.csv")
    return pub_df


# Get all publications of all coauthors of the author, and do de-duplication
def coauthor_data_crossref(orcid_id):
    df = crossref_author_by_orcid(orcid_id)
   
    authors_list = df["author_orcid"]
    frames = []
    frames.append(df)
    for coauthors_id in authors_list:
        # coauthors_id = coauthors_id.strip("[")
        # coauthors_id = coauthors_id.strip("]")
        # coauthors_id = coauthors_id.split(",")
        for id in coauthors_id:
            id = id.strip("' ")
            orcid_record = orcid.query_orcid_for_record(id)
            if orcid_record["person"]["addresses"]["address"]:
                country = orcid_record["person"]["addresses"]["address"][0]["country"]["value"]
            else:
                country = ""
            if country == "NL":
                if id != orcid_id:
                    df2 = crossref_author_by_orcid(id)
                    if not df2.empty:
                        frames.append(df2)
    new_df = pd.concat(frames)
    new_df2 = new_df.drop_duplicates(subset=["doi"], keep="first", ignore_index=True)
    # new_df2.to_csv(folderpath + "/" + fullname + "_coauthors_allpub.csv")
    return new_df2


# Read out all co-authorship relationships from stored publication data
def get_links_from_coauthor_rel(orcid_id):
    all_df = coauthor_data_crossref(orcid_id)
    authors_list = all_df["author_orcid"]
    links = []
    for coauthors_id in authors_list:
        # res = coauthors_id.strip("[")
        # res = res.strip("]")
        # res = res.split(",")

        if len(coauthors_id) >= 2: # Only choose the paper that has 2+ authors
            links = links + list(itertools.combinations(coauthors_id, 2)) # make coauthor pairs
    edge_data = pd.DataFrame()
    sources = []
    targets = []
    for link in links:
        sources.append(link[0].strip("' "))
        targets.append(link[1].strip("' "))
    edge_data["source"] = sources
    edge_data["target"] = targets
    # edge_data.to_csv(folderpath + "/" + fullname + "_coauthors_link.csv")
    return edge_data, links


# Group the authors in the stored data, 
# and generate the node dictionary that will be used to build the network
def assign_group_node(orcid_id):
    all_df = coauthor_data_crossref(orcid_id)
    dois = all_df["doi"]
    authors_orcid = all_df["author_orcid"]
    authors_name = all_df["authors"]

    clusters, idx2topics = orcid.orcid_lda_cluster(dois)
    node_data = pd.DataFrame()
    orcid_id = []
    name = []
    group = []
    for i in range(len(authors_orcid)):
        # authors_orcid[i] = authors_orcid[i].strip("[")
        # authors_orcid[i] = authors_orcid[i].strip("]")
        # authors_orcid[i] = authors_orcid[i].split(",")
        # authors_name[i] = authors_name[i].strip("[")
        # authors_name[i] = authors_name[i].strip("]")
        # authors_name[i] = authors_name[i].split(",")

        for j in range(len(authors_orcid[i])):
            temp_orcid = authors_orcid[i][j].strip("' ")
            temp_name = authors_name[i][j].strip("' ")
            orcid_id.append(temp_orcid)
            name.append(temp_name)
            group.append(clusters[dois[i]])

    node_data["orcid"] = orcid_id
    node_data["name"] = name
    node_data["group"] = group
    node_data["topics"] = idx2topics[group]

    new_node_data = node_data.drop_duplicates(
        subset=["orcid"], keep="first", ignore_index=True
    )

    return new_node_data

# Simple networkX & pyvis visualization
def build_networkx(orcid_id):
    node_data = assign_group_node(orcid_id)
    edge_data, link = get_links_from_coauthor_rel(orcid_id)
    weights = []
    for i in link:
        weights.append(link.count(i))
    edge_data["weight"] = weights

    # getting a group id
    groups = node_data.groupby("group")["orcid"].apply(list).reset_index()
    groups["group"] = groups.index

    # finding group id for each node from groups dataframe
    nodes = node_data.merge(groups, how="left", on=["group"])
    nodes["title"] = node_data[["name"]]
    nodes["label"] = node_data[["name"]]
    nodes = nodes.drop("orcid_y", axis=1).set_index("orcid_x")

    # Pyvis network
    N = Network(height=800, width="100%", bgcolor="#222222", font_color="white")
    N.toggle_hide_edges_on_drag(False)
    N.barnes_hut()

    # collecting node attributes for network x
    node_attrs = nodes.to_dict("index")

    # creating a network x graph from dataframes
    graph = nx.from_pandas_edgelist(edge_data, edge_attr=True)
    nx.set_node_attributes(graph, node_attrs)

    fullname = orcid.from_orcid_to_name(orcid_id)
    lastname = fullname.split(" ")[-1]
    N.from_nx(graph)
    N.show(lastname + "_datafile.html")
