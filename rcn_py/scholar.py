import pandas as pd
import itertools
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
    new_docs = []
    for j in docs:
        if ('pub_year' in j.keys()) and (j['pub_year'] > '2018'):
            new_docs.append(j)       
        
    # Search the authors of each publication
    df = pd.DataFrame()
    link = []
    for doc in new_docs:
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

