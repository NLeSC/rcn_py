import pandas as pd
import itertools
from pyvis.network import Network
from scholarly import scholarly



# use scholarly package
def scholar_search_coauthor(author_fullname):
    # Search author info by their name
    search_query_author = scholarly.search_author(author_fullname)
    author = scholarly.fill(next(search_query_author))
    
    # Get all the publication info of the author
    docs = []
    for i in range(len(author['publications'])):
        docs.append(author['publications'][i]['bib'])
        
    # Filter by year
    # new_docs = []
    # for j in docs:
    #         new_docs.append(j)       
        
    # Search the authors of each publication
    df = pd.DataFrame()
    link = []
    for doc in docs:
        search_pub = scholarly.search_pubs(doc['title'])
        pub_info = next(search_pub)
        # Build a dataframe containing authors' name and id
        temp_df = pd.DataFrame()
        temp_df['name'] = pub_info['bib']['author']
        temp_df['id'] = pub_info['author_id']
        
        # Build links
        id_list = temp_df['id']
        id_list_notnull = [i for i in id_list if i != '']
        link = link+list(itertools.combinations(id_list_notnull, 2))
        
        # Join dfs
        frames = pd.concat([df, temp_df], ignore_index=True)      
        df_notnull = frames[frames['id'] != '']
        df = df_notnull.drop_duplicates(subset = ['id'],keep='first', ignore_index=True)
        
    return df, link


def scholar_pyvis_network(fullname, node, link, au_group):
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
        #node["title"] = " Neighbors: \n" + " \n".join(neighbors)
        node["title"] = "Link to the author’s page:\n" + scholarly.search_author_id(node['id'])['url_picture']
        node["value"] = scholarly.search_author_id(node['id'])['citedby']
        node["label"] = scholarly.search_author_id(node['id'])['name']
       

    N.show(fullname + ".html")


def scholar_build_graph(G, sch_id, depth: int, bredth: int, last_author=[]):
    author_search = scholarly.search_author_id(sch_id)
    author = scholarly.fill(author_search,sections=['coauthors','indices','counts'])
    author_name = author['name']
    author_hin = author['hindex']
    author_ncite = author['citedby']
    G.add_node(author_name,hindex=author_hin,name=author_name,ncite=author_ncite)
    print("now at %s, depth=%d"%(author_name,depth))
    if depth>0:
        for coauthor in author['coauthors'][:int(bredth)]:
            G.add_edge(author_name,coauthor['name'])
            if coauthor['name'] not in last_author:
                last_author.append(author_name)
                scholar_build_graph(G,coauthor['scholar_id'],depth-1,bredth,last_author)
