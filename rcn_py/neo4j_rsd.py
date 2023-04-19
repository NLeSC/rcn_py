import requests
from neo4j import GraphDatabase
import requests
import time
from itertools import combinations
from rcn_py import orcid


# Get Scopus Author ID from ORCID
# This function solves the problem of overlap between the RSD and Scopus databases
# And also return author's preferred name
# MYAPIKEY = "3d120b6ddb7d069272dfc2bc68af4028"
def get_scopus_info_from_orcid(orcid, MYAPIKEY="3d120b6ddb7d069272dfc2bc68af4028"):
    time.sleep(0.5)
    
    url = "http://api.elsevier.com/content/search/author?query=ORCID%28"+orcid+"%29"

    header = {'Accept' : 'application/json', 
            'X-ELS-APIKey' : MYAPIKEY}
    resp = requests.get(url, headers=header)
    results = resp.json()

    if 'service-error' in results.keys():
        return '', '', ''
    elif 'error-response' in results.keys():
        time.sleep(1)
        get_scopus_info_from_orcid(orcid)

    elif 'error' in results['search-results']['entry'][0].keys():
        return '', '', ''
    else:
        scopus_author_id = results['search-results']['entry'][0]['dc:identifier'].split(':')[-1]

        # Get preferred name (instead of initials)
        name = results['search-results']['entry'][0]['preferred-name']
        preferred_name  = name['given-name'] + ' ' + name['surname']

        # Get scopus profile links
        links = results['search-results']['entry'][0]["link"]
        for l in links:
            if l['@ref'] == 'scopus-author':
                author_link = l['@href']

        return scopus_author_id, preferred_name, author_link
    

def get_scopus_result(authors, scopus_id_dict, preferred_name_dict, author_link_dict):
    
    for author in authors:
        if author['orcid'] and (author['orcid'] not in scopus_id_dict):
            scopus_id, preferred_name, author_link = get_scopus_info_from_orcid(author['orcid'])

            scopus_id_dict[author['orcid']] = scopus_id
            preferred_name_dict[author['orcid']] = preferred_name
            author_link_dict[author['orcid']] = author_link

    return scopus_id_dict, preferred_name_dict, author_link_dict

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

    for b in contributor_soft:
        b['name'] = b['given_names'] + ' ' + b['family_names']
        if b['orcid'] == None:
            b['orcid'] = orcid.name_to_orcid_id(b['name'])
    
    return projects, authors_proj, software, contributor_soft

def create_person_nodes(tx, authors, scopus_id_dict, preferred_name_dict, author_link_dict):
    # There is overlapping between RSD "project" and "software"
    for author in authors:
        if author['orcid']:
            author_scopus_id = scopus_id_dict[author['orcid']]
            preferred_name = preferred_name_dict[author['orcid']] 
            scopus_link = author_link_dict[author['orcid']]
        
            if len(preferred_name) == 0:
                preferred_name = author['name']

            if author['affiliation'] is None:
                if len(author_scopus_id) == 0:
                    tx.run("""
                            MERGE (p:Person {orcid: $orcid})
                            SET p.scopus_link = $link,
                                p.name= $name
                            """,
                            orcid = author['orcid'],
                            link = scopus_link,
                            name = preferred_name
                            )
                else:
                    tx.run("""
                            MERGE (p:Person {scopus_id: $scopus_id})
                            SET p.orcid= $orcid, 
                                p.scopus_link = $link,
                                p.name= $name
                            """,
                            scopus_id = author_scopus_id, 
                            orcid = author['orcid'],
                            link = scopus_link,
                            name = preferred_name
                            )
            else:
                if len(author_scopus_id) == 0:
                    tx.run("""
                        MERGE (p:Person {orcid: $orcid})
                        SET p.scopus_link = $link,
                            p.name= $name,
                            p.affiliation= $affiliation
                        """,
                        orcid = author['orcid'],
                        link = scopus_link,
                        name = preferred_name,
                        affiliation = author['affiliation']
                        )
                else:
                    tx.run("""
                        MERGE (p:Person {scopus_id: $scopus_id})
                        SET p.orcid= $orcid, 
                            p.scopus_link = $link,
                            p.name= $name,
                            p.affiliation= $affiliation
                        """,
                        scopus_id = author_scopus_id,
                        orcid = author['orcid'],
                        link = scopus_link,
                        name = preferred_name,
                        affiliation = author['affiliation']
                        )
    print("Author nodes added")
        

def create_project_nodes(tx, projects):

    # Create publication nodes which contains:
    #     doi (project do not have doi), 
    #     title, 
    #     year (There are many different dates in the record, 
    #         and there are many "end dates" that are after the current date，
    #         it is confusing.),
    #     description (or find keywords using topic models)
    for project in projects:
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
    print("Project nodes added")

def create_software_nodes(tx, softwares):
    # Create publication nodes which contains:
    #     doi (project do not have doi), 
    #     title, 
    #     year,
    #     description (or find keywords using topic models)
    for software in softwares:
        tx.run("""
            MERGE (s:Software {software_id: $software_id})
            SET s.doi = $doi,
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
    print("Software nodes added")

def create_author_project_edge(tx, authors, scopus_id_dict, preferred_name_dict, author_link_dict):
    # Create edges between authors and projects:
    #     author_name,
    #     title,
    #     year
    for author in authors:
        author_scopus_id = scopus_id_dict[author['orcid']]
        preferred_name = preferred_name_dict[author['orcid']] 
        # scopus_link = author_link_dict[author['orcid']]

        if len(preferred_name) == 0:
            preferred_name = author['name']

        if len(author_scopus_id) == 0:
            tx.run("""
                MATCH 
                    (n:Person {orcid: $orcid}),
                    (p:Project {project_id: $proj_id})
                MERGE (n)-[r:IS_AUTHOR_OF]->(p)
                ON CREATE SET 
                    r.author_name = $author_name,
                    r.title = p.title,
                    r.year = p.year
                """,
                orcid = author['orcid'],
                proj_id = author['project'],
                author_name = preferred_name
            )
        else:
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
    print("Author-Project relationship added")


def create_author_software_edge(tx, contributors, scopus_id_dict, preferred_name_dict, author_link_dict):
    # Create edges between authors and software:
    #     author_name,
    #     brand_name,
    #     year
    for contributor in contributors:
        contributor_scopus_id = scopus_id_dict[contributor['orcid']]
        preferred_name = preferred_name_dict[contributor['orcid']] 
        # scopus_link = author_link_dict[contributor['orcid']]
              
        if len(preferred_name) == 0:
            preferred_name = contributor['name']

        if len(contributor_scopus_id) == 0:
            tx.run("""
                MATCH 
                    (n:Person {orcid: $orcid}),
                    (s:Software {software_id: $software_id})
                MERGE (n)-[r:IS_AUTHOR_OF]->(s)
                ON CREATE SET 
                    r.author_name = $author_name,
                    r.title = s.title,
                    r.year = s.year
                """,
                orcid = contributor['orcid'],
                software_id = contributor['software'],
                author_name = preferred_name
            )
        else:
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
    print("Contributor-Software relationship added")