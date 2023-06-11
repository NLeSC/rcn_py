# There are the SQLite DB functions
# Not used in the later development
# Was Replaced by Neo4j graph database

import sqlite3
from itertools import combinations

import gensim
from crossref.restful import Works
from pyvis.network import Network
from rcn_py import orcid

"""
    author-paper table
    author info table
    publication table
"""

def insert_database(db_path, orcid_id, fullname):
    if len(orcid_id) == 0:
        orcid_id = orcid.name_to_orcid_id(fullname)
    orcid_record = orcid.query_orcid_for_record(orcid_id)
    # probably there is null value in every stage, which will occure an error
    if len(orcid_record["person"]["addresses"]["address"]) > 0:
        country = orcid_record["person"]["addresses"]["address"][0]["country"]["value"]
    else:
        country = ""

    docs = orcid.extract_works_section(orcid_record)

    con = sqlite3.connect(db_path)
    cur = con.cursor()
    works = Works()
    orcid_doi_value = []
    paper_value = []
    for doc in docs:
        doi, title = orcid.extract_doi(doc)
        # orcid_list, name_list = orcid.get_authors(doi)
        # country_list = []
        # for orc in
        # make insert value for orcid-doi
        orcid_doi_value.append((orcid_id, doi))

        w = works.doi(doi)
        # orcid_list, name_list = orcid.get_authors(doi)

        if w:
            if "abstract" in w.keys():
                abstract = w["abstract"]
            else:
                abstract = ""
        else:
            abstract = ""

        paper_value.append((doi, title, abstract))

    # author table (orcid, name, country)
    cur.execute(
        "INSERT or IGNORE INTO authors VALUES (?, ?, ?)", (orcid_id, fullname, country)
    )
    # publication table (doi, title, abstract)
    cur.executemany("INSERT or IGNORE INTO publications VALUES (?, ?, ?)", paper_value)
    # author-paper table (orcid, doi)
    cur.executemany(
        "INSERT or IGNORE INTO author_publication VALUES (?, ?)", orcid_doi_value
    )
    con.commit()
    con.close()

    return "Done"


# Retrieve the coauthors for publications of the person
def insert_coauthors_pub(db_path, fullname):
    orcid_id = orcid.name_to_orcid_id(fullname)
    orcid_record = orcid.query_orcid_for_record(orcid_id)
    if orcid_record is False:
        return
    docs = orcid.extract_works_section(orcid_record)

    for doc in docs:
        doi, title = orcid.extract_doi(doc)
        orcid_list, name_list = orcid.get_authors(doi)
        for i in range(len(orcid_list)):
            insert_database(db_path, orcid_list[i], name_list[i])

    return "Done!"


def insert_cocoauthors(database):
    con = sqlite3.connect(database)
    cur = con.cursor()
    cur.execute("SELECT doi FROM publications")
    all_dois = cur.fetchall()
    for doi in all_dois[:100]:
        orcid_list, name_list = orcid.get_authors(doi[0])
        if len(orcid_list) <= 1:
            continue
        orcid_doi_value = []
        for i in range(len(orcid_list[:10])):
            orcid_record = orcid.query_orcid_for_record(orcid_list[i])
            # probably there is null value in every stage, which will occure an error
            if len(orcid_record["person"]["addresses"]["address"]) > 0:
                country = orcid_record["person"]["addresses"]["address"][0]["country"][
                    "value"
                ]
            else:
                country = ""
            orcid_doi_value.append((orcid_list[i], doi))
            cur.execute(
                "INSERT or IGNORE INTO authors VALUES (?, ?, ?)",
                (orcid_list[i], name_list[i], country),
            )

        # cur.executemany("INSERT or IGNORE INTO authors VALUES (?, ?, ?)", author_info)
        cur.executemany(
            "INSERT or IGNORE INTO author_publication VALUES (?, ?)", orcid_doi_value
        )

    con.commit()
    con.close()
    return "Done"


def pub_cluster(cur):
    res = cur.execute("SELECT doi, title, abstract FROM publications")
    all_pub = res.fetchall()
    cleaned_corpus = []
    dois = []
    for pub in all_pub:
        dois.append(pub[0])
        cleaned_corpus.append(orcid.preprocess(pub[1] + " " + pub[2]))
    dictionary = gensim.corpora.Dictionary(cleaned_corpus)
    corpus = [dictionary.doc2bow(text) for text in cleaned_corpus]

    lda_model = gensim.models.LdaMulticore(
        corpus, num_topics=8, id2word=dictionary, passes=10, workers=2
    )

    idx2topics = {}
    for idx, topic in lda_model.print_topics(-1):
        idx2topics[idx] = topic

    clusters = {}
    for i in range(len(cleaned_corpus)):
        scores = []
        topics = []
        for j1, j2 in lda_model[corpus[i]]:
            topics.append(j1)
            scores.append(j2)
            clusters[dois[i]] = scores.index(max(scores))
    return clusters, idx2topics


def fetch_relationships(cur):
    author_res = cur.execute("""
    SELECT GROUP_CONCAT(orcid, ',') AS orcids 
    FROM author_publication 
    WHERE doi != 'None' 
    GROUP BY doi 
    HAVING COUNT(*) > 1
    """)
    all_authors = author_res.fetchall()
    coauthor_links = []
    for au in all_authors:
        au = au[0].strip("(')")
        au = au.split(",")
        coauthor_links = coauthor_links + list(combinations(au, 2))
    return coauthor_links


def author_cluster(cur, clusters):
    author_res = cur.execute("""
    SELECT orcid
    GROUP_CONCAT(doi,',') 
    FROM author_publication 
    WHERE doi != 'None' 
    GROUP BY orcid
    """)
    
    orc_doi = author_res.fetchall()
    au_group = {}
    for au_pub in orc_doi:
        pubs = au_pub[1].strip("'")
        doi_list = pubs.split(",")
        groups = []
        for doi in doi_list:
            groups.append(clusters[doi])
        au_group[au_pub[0]] = max(groups, key=groups.count)
    return au_group


def build_network_database(db_path, name):
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    clusters, idx2topics = pub_cluster(cur)
    link = fetch_relationships(cur)
    res_all_authors = cur.execute("SELECT orcid, name FROM authors")
    all_authors = res_all_authors.fetchall()
    group = author_cluster(cur, clusters)

    sources = []
    targets = []
    weights = []

    for i in link:
        sources.append(i[0])
        targets.append(i[1])
        weights.append(link.count(i))

    id2name = {}
    for author in all_authors:
        id2name[author[0]] = author[1]

    # Pyvis network
    N = Network(height=800, width="100%", bgcolor="#222222", font_color="white")
    N.toggle_hide_edges_on_drag(False)
    N.barnes_hut()

    edge_data = zip(sources, targets, weights)

    for e in edge_data:
        src = e[0]
        dst = e[1]
        w = e[2]

        N.add_node(src, src, title=src, group=group[src])
        N.add_node(dst, dst, title=dst, group=group[dst])
        N.add_edge(src, dst, value=w)

    # add neighbor data to node hover data
    for node in N.nodes:
        node["title"] = node["id"]
        node["label"] = cur.execute(
            "SELECT name FROM authors WHERE orcid == ?", (node["id"],)
        ).fetchall()[0][0]

    cur.close()

    N.show(name + ".html")
