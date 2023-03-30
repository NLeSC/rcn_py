import requests
import sqlite3
import sys
sys.path.append("..")
from rcn_py import orcid
import gensim
from itertools import combinations
from pyvis.network import Network
import networkx as nx

def create_rsd_database(db_path):
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    # Create a project table
    cur.execute("CREATE TABLE project (id primary key, title, description)")

    # Create a project member table where the id is unique, 
    # the data includes author info and software id,
    # N-to-N mapping
    cur.execute("""
    CREATE TABLE author(
        id primary key, project, orcid, given_name, family_name, affiliation, 
        FOREIGN KEY(project) 
        REFERENCES project(id))
        """)
    
    # Create a software table
    cur.execute("CREATE TABLE software(id primary key, doi, brand_name, description)")

    # Create a software contributor table where the id is unique, 
    # the data includes contributor info and software id,
    # N-to-N mapping
    cur.execute("""
    CREATE TABLE contributor(
        id primary key, software, orcid, given_name, family_name, affiliation, 
        FOREIGN KEY(software) 
        REFERENCES software(id))
        """)
    
    con.commit()
    con.close()
    return "Created"


def store_rsd(db_path):
    response_project = requests.get(
        "https://research-software-directory.org/api/v1/project?select=id,title,description"
        )
    response_author = requests.get(
        "https://research-software-directory.org/api/v1/team_member?select=id,project,orcid,given_names,family_names, affiliation"
        )
    response_software = requests.get(
        "https://research-software-directory.org/api/v1/software?select=id,concept_doi,brand_name, description"
        )
    response_contributor = requests.get(
        "https://research-software-directory.org/api/v1/contributor?select=id,software,orcid,given_names,family_names,affiliation"
        )
    
    projects = response_project.json()
    authors_proj = response_author.json()
    software = response_software.json()
    contributor_soft = response_contributor.json()

    con = sqlite3.connect(db_path)
    cur = con.cursor()
    for p in projects:
        cur.execute("INSERT or IGNORE INTO project VALUES (?, ?, ?)", 
                    (p['id'], p['title'], p['description'])
            )
    
    for a in authors_proj:
        if a['orcid'] == None:
            a['orcid'] = orcid.name_to_orcid_id(a['given_names'] + ' ' + a['family_names'])
        cur.execute(
            "INSERT or IGNORE INTO author VALUES (?, ?, ?, ?, ?, ?)", 
            (a['id'], a['project'], a['orcid'], a['given_names'], a['family_names'], a['affiliation'])
            )
    
    for s in software:
        cur.execute("INSERT or IGNORE INTO software VALUES (?, ?, ?, ?)", 
                    (s['id'], s['concept_doi'], s['brand_name'], s['description']))
    
    for c in contributor_soft:
        if c['orcid'] == None:
            c['orcid'] = orcid.name_to_orcid_id(c['given_names'] + ' ' + c['family_names'])
        cur.execute("INSERT or IGNORE INTO contributor VALUES (?, ?, ?, ?, ?, ?)", 
                    (c['id'], c['software'], c['orcid'], c['given_names'], c['family_names'], c['affiliation']))
    con.commit()
    con.close()
    return "Done"



# Please choose a record_type: "project" or "software"
def project_software_cluster(db_path, record_type):
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    if record_type == 'project':
        res = cur.execute("SELECT id, title, description FROM project")
    elif record_type == 'software':
        res = cur.execute("SELECT id, brand_name, description FROM software")
    else:
        return "Please choose the data you wish to access, project or software."
    id_description = res.fetchall()

    cleaned_corpus = []
    ids = []
    for pub in id_description:
        ids.append(pub[0])
        if pub[2] == None:
            cleaned_corpus.append(orcid.preprocess(pub[1]))
        else:
            cleaned_corpus.append(orcid.preprocess(pub[1]+' '+pub[2]))
    cur.close()
    
    dictionary = gensim.corpora.Dictionary(cleaned_corpus) 
    corpus = [dictionary.doc2bow(text) for text in cleaned_corpus]

    lda_model =  gensim.models.LdaMulticore(corpus, 
                                    num_topics = 8, 
                                    id2word = dictionary,                                    
                                    passes = 10,
                                    workers = 2)
        
    idx2topics = {}
    for idx, topic in lda_model.print_topics(-1):
        idx2topics[idx] = topic
    
    clusters = {}
    for i in range(len(cleaned_corpus)):
        scores = []
        topics = []
        for j1,j2 in lda_model[corpus[i]]:
            topics.append(j1)
            scores.append(j2)
            clusters[ids[i]] = scores.index(max(scores))

    return clusters, idx2topics


def author_cluster(db_path, type, clusters):
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    if type == 'project':
        res = cur.execute("""
        SELECT orcid, GROUP_CONCAT(project,',') 
        FROM author 
        GROUP BY orcid
        """)
    elif type == 'software':
        res = cur.execute("""
        SELECT orcid, GROUP_CONCAT(software,',') 
        FROM contributor 
        GROUP BY orcid
        """)
    else:
        return "Please choose the data you wish to access, project or software."
    orc_id = res.fetchall()

    au_group = {}
    for au_pub in orc_id:
        pubs = au_pub[1].strip('\'')
        id_list = pubs.split(',')
        set_id_list = list(set(id_list))
        groups = []
        for id in set_id_list:
            groups.append(clusters[id])
        au_group[au_pub[0]] = max(groups,key=groups.count)
    cur.close()
    return au_group
    


def rsd_relationship(db_path, type):
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    if type == 'project':
        res = cur.execute("""
        SELECT GROUP_CONCAT(orcid, ',') AS orcids 
        FROM author 
        GROUP BY project 
        HAVING COUNT(*) > 1
        """)
    elif type == 'software':
        res = cur.execute("""
        SELECT GROUP_CONCAT(orcid, ',') AS orcids 
        FROM contributor 
        GROUP BY software 
        HAVING COUNT(*) > 1
        """)
    else:
        return "Please choose the data you wish to access, project or software."
    coauthor = res.fetchall()

    coauthor_links = []
    for au in coauthor:
        au = au[0].strip('(\')')
        au = au.split(',')
        coauthor_links = coauthor_links+list(combinations(au, 2))
    cur.close()
    return coauthor_links


# pyvis
def build_network_pyvis(db_path, type):
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    clusters, idx2topics = project_software_cluster(type)
    link = rsd_relationship(type)
    group = author_cluster(type, clusters)
    
    if type == 'project':
        res_authors = cur.execute("""
        SELECT orcid, given_name, family_name 
        FROM author 
        GROUP BY orcid
        """)
    elif type == 'software':
        res_authors = cur.execute("""
        SELECT orcid, given_name, family_name 
        FROM contributor 
        GROUP BY orcid
        """)
    else:
        return "Please choose the data you wish to access, project or software."
    all_authors = res_authors.fetchall()
    
    sources = []
    targets = []
    weights = []

    for i in link:
        sources.append(i[0])
        targets.append(i[1])
        weights.append(link.count(i))

    id2name = {}
    for author in all_authors:
        id2name[author[0]] = author[1]+' '+author[2]   
    
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
        node["title"] = idx2topics[group[node['id']]]
        node["label"] = id2name[node["id"]]

    cur.close()

    N.show(type+"_rsd.html")
    return "html file is created"



# gephi
def build_network_gephi(db_path, type):
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    clusters, idx2topics = project_software_cluster(type)
    link = rsd_relationship(type)
    group = author_cluster(type, clusters)
    
    if type == 'project':
        res_authors = cur.execute("""
        SELECT orcid, given_name, family_name 
        FROM author 
        GROUP BY orcid
        """)
    elif type == 'software':
        res_authors = cur.execute("""
        SELECT orcid, given_name, family_name 
        FROM contributor 
        GROUP BY orcid
        """)
    else:
        return "Please choose the data you wish to access, project or software."
    all_authors = res_authors.fetchall()
    
    sources = []
    targets = []
    weights = []
    all_node_in_link = []

    for i in link:
        sources.append(i[0])
        targets.append(i[1])
        weights.append(link.count(i))
        all_node_in_link.append(i[0])
        all_node_in_link.append(i[1])

    id2name = {}
    for author in all_authors:
        id2name[author[0]] = author[1]+' '+author[2]   
    
    # networkx
    G = nx.Graph()

    edge_data = zip(sources, targets, weights)

    for e in edge_data:
        src = e[0]
        dst = e[1]
        w = e[2]

        G.add_node(src, group=group[src], title=idx2topics[group[src]], label=id2name[src], size=all_node_in_link.count(src))
        G.add_node(dst, group=group[dst], title=idx2topics[group[dst]], label=id2name[dst], size=all_node_in_link.count(dst))
        G.add_edge(src, dst, weight=w)

    cur.close()

    out_path =  type+ '_rsd.gexf'
   
    nx.write_gexf(G,out_path)
    return "gexf file is created"