from crossref.restful import Works
import requests
import pandas as pd


# Query ORCID by a fullname
headers = {
    'Accept': 'application/vnd.orcid+json',
}
def name_to_orcid_id(name):
    orcid_id = None
    
    params = (
        ('q',name),
    )
    response = requests.get('https://pub.orcid.org/v3.0/search/', headers=headers, params=params)
    temp = response.json()
    if len(temp):
        orcid_id = temp['result'][0]['orcid-identifier']['path']
    return orcid_id


# Extract authors from a doc
def get_authors(doi):
    works = Works()
    metadata = works.doi(doi)
    # It's possible that the acquired  
    if (metadata) and ('author' in metadata.keys()):
        authors = metadata['author']
        orcid_list = []
        author_names = []

        for i in authors:
            if 'ORCID' in i.keys():
                orcid_id_split = i['ORCID'].split("http://orcid.org/")[1]
                orcid_list.append(orcid_id_split)
            else:
                orcid_id_by_name = name_to_orcid_id(i['given']+' '+i['family'])
                orcid_list.append(orcid_id_by_name)
            author_names.append(i['given']+' '+i['family'])
        return orcid_list, author_names
    else:
        return [],[]


# URL for ORCID API
ORCID_RECORD_API = "https://pub.orcid.org/v3.0/"

# query ORCID for an ORCID record
def query_orcid_for_record(orcid_id):

    response = requests.get(url = requests.utils.requote_uri(ORCID_RECORD_API + orcid_id),
                          headers = {'Accept': 'application/json'})
    response.raise_for_status()
    result=response.json()
    return result

# query author name from ORCID
def from_orcid_to_name(orcid_id):
    orcid_record = query_orcid_for_record(orcid_id)
    name_attr = orcid_record['person']['name']
    name = name_attr['given-names']['value'] + ' ' + name_attr['family-name']['value']


# Extract works from ORCID
def extract_works_section(orcid_record):
    works = orcid_record['activities-summary']['works']['group']
    return works

# Extract title and DOI
def extract_doi(work):
    work_summary = work['work-summary'][0]
    title = work_summary['title']['title']['value']
    dois =  [doi['external-id-value'] for doi in work_summary['external-ids']['external-id'] if doi['external-id-type']=="doi"]
    # if there is a DOI, we can extract the first one
    doi = dois[0] if dois else None
    doi = str(doi)
    return doi, title

def get_coauthors(full_name):
    orcid_id = name_to_orcid_id(full_name)
    orcid_record = query_orcid_for_record(orcid_id)
    docs = extract_works_section(orcid_record)
    all_orcid = []
    all_names = []
        
    for doc in docs:
        dois, titles = extract_doi(doc)
        
        for doi in dois:
            orcid_list, name_list = get_authors(doi)
            all_orcid += orcid_list
            all_names += name_list
        
    df = pd.DataFrame()
    df['orcid'] = all_orcid
    df['name'] = all_names
    new_df = df.drop_duplicates(subset = ['orcid'],keep='first', ignore_index=True)
    
    return new_df
    