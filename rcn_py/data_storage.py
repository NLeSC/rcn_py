import orcid
import pandas as pd
from scholarly import scholarly
from crossref.restful import Works
import itertools
import networkx as nx
from pyvis.network import Network
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
nltk.download("stopwords")
nltk.download('wordnet')
stop_words = set(stopwords.words("english"))
wnl = WordNetLemmatizer()

def get_scholar_data(fullname, folderpath):
    # Search author info by their name
    search_query_author = scholarly.search_author(fullname)
    author = scholarly.fill(next(search_query_author))
    # Get all the publication info of the author
    docs = []
    for i in range(len(author['publications'])):
        docs.append(author['publications'][i]['bib'])

    title = []
    coauthor_name = []
    abstract = []

    pub_df = pd.DataFrame()
    for doc in docs:
        search_pub = scholarly.search_pubs(doc['title'])
        pub_info = next(search_pub)
        title.append(pub_info['bib']['title'])
        coauthor_name.append(pub_info['bib']['author'])
        abstract.append(pub_info['bib']['abstract'])
    pub_df['title'] = title
    pub_df['authors'] = coauthor_name
    pub_df['abstarct'] = abstract

    pub_df.to_csv(folderpath+'/'+fullname+"_scholar.csv")
    return pub_df


def get_crossref_data_by_orcid(orcid_id):
    # Extract author info using ORCID
    orcid_record = orcid.query_orcid_for_record(orcid_id)
    if orcid_record == False:
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
            if 'abstract' in w.keys():
                abstract.append(w['abstract'])
            else:
                abstract.append('')
        else:
            abstract.append('')
        coauthor_name.append(name_list)
        coauthor_orcid.append(orcid_list)
        
    pub_df = pd.DataFrame()
    pub_df['title'] = title_list
    pub_df['doi'] = doi_list
    pub_df['authors'] = coauthor_name
    pub_df['abstarct'] = abstract
    pub_df['author_orcid'] = coauthor_orcid

    return pub_df

        

        

# Store all publication info of one person
def get_crossref_data_by_name(fullname, folderpath):
    # Extract author info using ORCID
    orcid_id = orcid.name_to_orcid_id(fullname)
    orcid_record = orcid.query_orcid_for_record(orcid_id)
    if orcid_record == False:
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
            if 'abstract' in w.keys():
                abstract.append(w['abstract'])
            else:
                abstract.append('')
        else:
            abstract.append('')
        coauthor_name.append(name_list)
        coauthor_orcid.append(orcid_list)
        
    pub_df = pd.DataFrame()
    pub_df['title'] = title_list
    pub_df['doi'] = doi_list
    pub_df['authors'] = coauthor_name
    pub_df['abstarct'] = abstract
    pub_df['author_orcid'] = coauthor_orcid

    pub_df.to_csv(folderpath+'/'+fullname+"_crossref.csv")
    return pub_df

        
# Get all publications of all coauthors and do de-duplication
def coauthor_data_from_csv(fullname, folderpath):
    orcid_id = orcid.name_to_orcid_id(fullname)
    df = pd.read_csv(folderpath+'/'+fullname+"_crossref.csv")
    authors_list = df['author_orcid']
    frames = []
    frames.append(df)
    for coauthors_id in authors_list:
        coauthors_id = coauthors_id.strip('[')
        coauthors_id = coauthors_id.strip(']')
        coauthors_id = coauthors_id.split(',')
        for id in coauthors_id:
            id = id.strip('\' ')
            if id != orcid_id:
                df2 = get_crossref_data_by_orcid(id)
                if not df2.empty:
                    frames.append(df2)
    new_df = pd.concat(frames)
    new_df2 = new_df.drop_duplicates(subset = ['doi'],keep='first', ignore_index=True)
    new_df2.to_csv(folderpath+'/'+fullname+"_coauthors_allpub.csv")
    return new_df2
   
    
   
    


# Read out all co-authorship relationships from stored publication data
def get_links_from_csv(fullname, folderpath):
    all_df = pd.read_csv(folderpath+'/'+fullname+"_coauthors_allpub.csv")
    authors_list = all_df['author_orcid']
    link = []
    for coauthors_id in authors_list:
        res = coauthors_id.strip('[')
        res = res.strip(']')
        res = res.split(',')
        if len(res) >=2:
            link = link+list(itertools.combinations(res, 2))
    edge_data = pd.DataFrame()
    sources = []
    targets = []
    for l in link:
        sources.append(l[0])
        targets.append(l[1])
    edge_data['source'] = sources
    edge_data['target'] = targets
    edge_data.to_csv(folderpath+'/'+fullname+"_coauthors_link.csv")
    return edge_data, link
    

# Group the authors in the stored data, and generate the node dictionary that will be used to build the network
def assign_group_node(fullname, folderpath):
    all_df = pd.read_csv(folderpath+'/'+fullname+"_coauthors_allpub.csv")
    dois = all_df['doi']
    authors_orcid = all_df['author_orcid']
    authors_name = all_df['authors']

    clusters = orcid.orcid_lda_cluster(dois)
    node_data = pd.DataFrame()
    orcid_id = []
    name = []
    group = []
    for i in range(len(authors_orcid)):
        authors_orcid[i] = authors_orcid[i].strip('[')
        authors_orcid[i] = authors_orcid[i].strip(']')
        authors_orcid[i] = authors_orcid[i].split(',')
        authors_name[i] = authors_name[i].strip('[')
        authors_name[i] = authors_name[i].strip(']')
        authors_name[i] = authors_name[i].split(',')
        
        for j in range(len(authors_orcid[i])):
            orcid_id.append(authors_orcid[i][j])
            name.append(authors_name[i][j])
            group.append(clusters[dois[i]])

    node_data['orcid'] = orcid_id
    node_data['name'] = name
    node_data['group'] = group
    
    new_node_data = node_data.drop_duplicates(subset = ['orcid'],keep='first', ignore_index=True)

    return new_node_data
    


def build_network_by_datafile(fullname, folderpath, outputpath):
    node_data = assign_group_node(fullname, folderpath)
    edge_data, link = get_links_from_csv(fullname, folderpath)
    weights = []
    for i in link:
        weights.append(link.count(i))
    edge_data['weight'] = weights
    
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

    lastname = fullname.split(' ')[-1]
    N.from_nx(graph)
    N.show(lastname+'_datafile.html')



