import requests
from neo4j import GraphDatabase
import requests
from itertools import combinations
from rcn_py import orcid


# Get Scopus Author ID from ORCID
# This function solves the problem of overlap between the RSD and Scopus databases
# And also return author's preferred name
# MYAPIKEY = "3d120b6ddb7d069272dfc2bc68af4028"
def get_scopus_info_from_orcid(orcid, MYAPIKEY="3d120b6ddb7d069272dfc2bc68af4028"):

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
        "https://research-software-directory.org/api/v1/project?select=id,title,created_at,description"
        )
    response_author = requests.get(
        "https://research-software-directory.org/api/v1/team_member?select=id,project,orcid,given_names,family_names, affiliation"
        )
    response_software = requests.get(
        "https://research-software-directory.org/api/v1/software?select=id,concept_doi,brand_name,created_at,description"
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
    author_scopus_id, preferred_name = get_scopus_info_from_orcid(author['orcid'])
    
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
                """,
                scopus_id = author_scopus_id,
                orcid = author['orcid'],
                name = preferred_name,
                affiliation = author['affiliation']
                )
        

def create_project_nodes(tx, project):

    # Create publication nodes which contains:
    #     doi (project do not have doi), 
    #     title, 
    #     year (There are many different dates in the record, 
    #         and there are many "end dates" that are after the current date，
    #         it is confusing.),
    #     description (or find keywords using topic models)

    tx.run("""
            MERGE (p:Project {project_id: $proj_id})
            SET p.title = $title,
                p.year = $year,
                p.description = $description
            """,
            proj_id = project['id'],
            title = project['title'],
            year = project['created_at'][0:4],
            description = project['description']
            )

def create_software_nodes(tx, software):
    # Create publication nodes which contains:
    #     doi (project do not have doi), 
    #     title, 
    #     year,
    #     description (or find keywords using topic models)

    tx.run("""
            MERGE (s:Software {software_id: $software_id})
            SET s.doi = $doi
                s.title = $brand_name,
                s.year = $year,
                s.description = $description
            """,
            software_id = software['id'],
            doi = software['concept_doi'],
            brand_name = software['brand_name'],
            year = software['created_at'][0:4],
            description = software['description']
            )

def create_author_project_edge(tx, author):

    # Create edges between authors and projects:
    #     author_name,
    #     title,
    #     year

    author_scopus_id, preferred_name = get_scopus_info_from_orcid(author['orcid'])

    tx.run("""
            MATCH 
                (n:Person {scopus_id: $scopus_id}),
                (p:Project {project_id: $proj_id})
            MERGE (n)-[r:IS_AUTHOR_OF]->(p)
            ON CREATE SET 
                r.author_name = $author_name,
                r.title = p.title,
                r.year = p.year
            """,
            scopus_id = author_scopus_id,
            proj_id = author['project'],
            author_name = preferred_name
        )


def create_author_software_edge(tx, contributor):

    # Create edges between authors and software:
    #     author_name,
    #     brand_name,
    #     year

    contributor_scopus_id, preferred_name = get_scopus_info_from_orcid(contributor['orcid'])

    tx.run("""
            MATCH 
                (n:Person {scopus_id: $scopus_id}),
                (s:Software {software_id: $software_id})
            MERGE (n)-[r:IS_AUTHOR_OF]->(s)
            ON CREATE SET 
                r.author_name = $author_name,
                r.title = s.title,
                r.year = s.year
            """,
            scopus_id = contributor_scopus_id,
            software_id = contributor['software'],
            author_name = preferred_name
        )
