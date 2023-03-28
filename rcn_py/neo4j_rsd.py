import requests
from neo4j import GraphDatabase
import requests
from itertools import combinations
from rcn_py import orcid


# Get Scopus Author ID from ORCID
# This function solves the problem of overlap between the RSD and Scopus databases
# And also return author's preferred name
# MYAPIKEY = "3d120b6ddb7d069272dfc2bc68af4028"
def get_scoous_info_from_orcid(orcid, MYAPIKEY="3d120b6ddb7d069272dfc2bc68af4028"):

    url = "http://api.elsevier.com/content/search/author?query=ORCID%28"+orcid+"%29"

    header = {'Accept' : 'application/json', 
            'X-ELS-APIKey' : MYAPIKEY}
    resp = requests.get(url, headers=header)
    results = resp.json()
    if 'service-error' in results.keys():
        return 
    else:
        scopus_author_id = results['search-results']['entry'][0]['dc:identifier'].split(':')[-1]
        name = results['search-results']['entry'][0]['preferred-name']
        preferred_name  = name['surname'] + ' ' + name['initials']
        return scopus_author_id, preferred_name
    

def request_rsd_data():
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

    for a in authors_proj:
        a['name'] = a['given_names'] + ' ' + a['family_names']
        if a['orcid'] == None:
            a['orcid'] = orcid.name_to_orcid_id(a['name'])
    
    return projects, authors_proj, software, contributor_soft

def create_person_nodes(tx, author):
    # There is overlapping between RSD "project" and "software"
    author_scopus_id, preferred_name = get_scoous_info_from_orcid(author['orcid'])
    
    if author['affiliation'] is None:
        tx.run("""
                MERGE (p:Person {scopus_id: $scopus_id})
                SET p.orcid= $orcid, 
                    p.name= $name
                )""",
                scopus_id = author_scopus_id, 
                orcid = author['orcid'],
                name = preferred_name
                )
    else:
        tx.run("""
                MERGE (p:Person {scopus_id: $scopus_id})
                SET p.orcid= $orcid, 
                    p.name= $person.name,
                    p.affiliation= $affiliation
                )""",
                scopus_id = author_scopus_id,
                orcid = author['orcid'],
                name = preferred_name,
                affiliation = author['affiliation']
                )
        

def create_project_software_nodes():
    TODO = """
    Create publication nodes which contains:
        doi (project do not have doi), 
        title, 
        year (There are many different dates in the record, 
            and there are many "end dates" that are after the current date，
            it is confusing.),
        description (or find keywords using topic models)

    """

def create_author_edge():
    TODO = """
    Create edges between authors and publications:
        author_name,
        title, 
        year
    """