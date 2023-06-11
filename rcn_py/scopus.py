import itertools
import pandas as pd
from pybliometrics.scopus import AuthorRetrieval, AuthorSearch
from pyvis.network import Network
from rcn_py import topic_modeling


def get_hindex(au_id):
    au = AuthorRetrieval(au_id)
    return au.h_index


def filter_country(author_list, country_code):
    filtered_authors = []
    for i in author_list:
        aff_list = AuthorRetrieval(i).affiliation_current
        for aff_cur in aff_list:
            if aff_cur.country_code == country_code:
                filtered_authors.append(i)
                break
    return filtered_authors


def coauthor_depth(author_id, depth, node_retrieved):
    au = AuthorRetrieval(author_id)
    docs = pd.DataFrame(au.get_documents())
    # Get clusters of docs
    docs = topic_modeling.lda_cluster(docs)
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
        for j in coau_id:
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
        link = link + list(itertools.combinations(sorted_new_coauid, 2))
        # Do recursion (increase depth of the network)
        if depth > 0:
            for j in sorted_new_coauid:
                if j not in node_retrieved:
                    coauthor_depth(j, depth - 1, node_retrieved)
    return all_node, link, au_group


def get_coauthor(author_first, author_last, depth):
    s = AuthorSearch(
        "AUTHLAST(" + author_last + ") and AUTHFIRST(" + author_first + ")"
    )
    author_id = s.authors[0].eid.split("-")[-1]

    node_retrieved = []
    node, link, au_group = coauthor_depth(author_id, depth, node_retrieved)
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

        N.add_node(src, src, title=src, group=au_group[src])
        N.add_node(dst, dst, title=dst, group=au_group[dst])
        N.add_edge(src, dst, value=w)

    neighbor_map = N.get_adj_list()

    # add neighbor data to node hover data
    for node in N.nodes:
        neighbors = []
        for neighbor_id in neighbor_map[node["id"]]:
            neigh = AuthorRetrieval(neighbor_id)
            neighbors.append(neigh.given_name + " " + neigh.surname)
        # node["title"] = " Neighbors: \n" + " \n".join(neighbors)
        node["title"] = (
            "Link to the author’s API page:\n" + AuthorRetrieval(node["id"]).self_link
        )
        node["value"] = get_hindex(node["id"])
        node["label"] = (
            AuthorRetrieval(node["id"]).given_name
            + " "
            + AuthorRetrieval(node["id"]).surname
        )

    N.show(author_last + ".html")
