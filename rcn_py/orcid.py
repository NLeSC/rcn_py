from crossref.restful import Works
import requests


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
