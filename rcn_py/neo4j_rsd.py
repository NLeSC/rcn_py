import requests
from rcn_py import orcid
from rcn_py import scopus


# Get Scopus Author ID from ORCID
# This function is able to solve the problem of overlap between the RSD and Scopus databases
# And also return author's preferred name
# MYAPIKEY = "3d120b6ddb7d069272dfc2bc68af4028"
    

def get_scopus_result(authors, scopus_id_dict, preferred_name_dict, author_link_dict):
    """
        This function takes as inputs a list of authors, and three dictionaries which map an author's ORCID
        to their Scopus ID, preferred name, and author link, respectively. 

        For each author in the authors list, if they have an ORCID and it is not already in the Scopus ID dictionary,
        their Scopus information is fetched and added to all three dictionaries.

        Parameters:
        authors (list): A list of authors. Each author is expected to be a dictionary with an 'orcid' key.
        scopus_id_dict (dict): A dictionary that maps an author's ORCID to their Scopus ID.
        preferred_name_dict (dict): A dictionary that maps an author's ORCID to their preferred name.
        author_link_dict (dict): A dictionary that maps an author's ORCID to their author link.

        Returns:
        scopus_id_dict (dict): The updated Scopus ID dictionary.
        preferred_name_dict (dict): The updated preferred name dictionary.
        author_link_dict (dict): The updated author link dictionary.
    """
    # Iterate over each author in the authors list
    for author in authors:
        # If the author has an ORCID and it's not already in the Scopus ID dictionary
        if author['orcid'] and (author['orcid'] not in scopus_id_dict):
            # use the ORCID to get the Scopus ID, preferred name, and author link for the author
            scopus_id, preferred_name, author_link = scopus.get_scopus_info_from_orcid(author['orcid'])
            # Add the newly fetched information to their respective dictionaries
            scopus_id_dict[author['orcid']] = scopus_id
            preferred_name_dict[author['orcid']] = preferred_name
            author_link_dict[author['orcid']] = author_link

    # Return the updated dictionaries
    return scopus_id_dict, preferred_name_dict, author_link_dict

# Add constraint forPerson nodes, Product nodes and Software nodes
def rsd_add_constraint(tx):
    """
    This function is used to add constraints to the nodes in a Neo4j database. 
    It ensures that the 'id'/'doi' property of Project/Software nodes and the 'orcid' property of Person nodes are unique.
    """

    # This Cypher command creates a unique constraint on the 'project_id' property of Project nodes.
    # If a constraint by the name 'proj_id' does not exist, it will be created.
    tx.run("""
            CREATE CONSTRAINT proj_id IF NOT EXISTS
            FOR (p:Project) REQUIRE p.doi IS UNIQUE
            """)
    # This Cypher command creates a unique constraint on the 'soft_doi' property of Software nodes.
    # If a constraint by the name 'soft_doi' does not exist, it will be created.
    tx.run("""
            CREATE CONSTRAINT soft_doi IF NOT EXISTS
            FOR (s:Software) REQUIRE s.doi IS UNIQUE
            """)
    # This Cypher command creates a unique constraint on the 'scopus_id' property of Person nodes.
    # If a constraint by the name 'scopus_id' does not exist, it will be created.
    tx.run("""
            CREATE CONSTRAINT orcid IF NOT EXISTS
            FOR (n:Person) REQUIRE n.orcid IS UNIQUE
            """)

def request_rsd_data():
    """
    This function sends GET requests to the RSD API to retrieve data about
    projects, team members (authors), software and contributors. It then processes this data by adding full
    names and fetching missing ORCIDs, and returns it.

    Returns:
    projects (list): List of project data fetched from the API.
    authors_proj (list): List of author data fetched from the API.
    software (list): List of software data fetched from the API.
    contributor_soft (list): List of contributor data fetched from the API.
    """
    # Send GET requests to the RSD API and store the responses
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
        
    # Convert the responses to JSON format
    projects = response_project.json()
    authors_proj = response_author.json()
    software = response_software.json()
    contributor_soft = response_contributor.json()

    # For each author, create a 'name' field and, if their ORCID is missing, generate one based on their name
    for a in authors_proj:
        a['name'] = a['given_names'] + ' ' + a['family_names']
        if a['orcid'] == None:
            a['orcid'] = orcid.name_to_orcid_id(a['name'])
    # For each contributor, create a 'name' field and, if their ORCID is missing, generate one based on their name
    for b in contributor_soft:
        b['name'] = b['given_names'] + ' ' + b['family_names']
        if b['orcid'] == None:
            b['orcid'] = orcid.name_to_orcid_id(b['name'])
    
    return projects, authors_proj, software, contributor_soft

def create_person_nodes(tx, authors, scopus_id_dict, preferred_name_dict, author_link_dict):
    """
    This function is used to create person nodes in a Neo4j database. It goes through each author, fetches their
    Scopus ID, preferred name and Scopus link, and then creates a new node in the database for them, or updates 
    the existing one if it already exists.

    Parameters:
    tx (neo4j.Session): A Neo4j session for running Cypher commands.
    authors (list): A list of authors.
    scopus_id_dict (dict): A dictionary that maps an author's ORCID to their Scopus ID.
    preferred_name_dict (dict): A dictionary that maps an author's ORCID to their preferred name.
    author_link_dict (dict): A dictionary that maps an author's ORCID to their author link.
    """
    # Iterate over each author in the list
    for author in authors:
        if author['orcid']:

            # If the author's ORCID is in the Scopus ID dictionary, get their Scopus ID, preferred name, and Scopus link
            # Otherwise, fetch this information using the get_scopus_info_from_orcid function
            if author['orcid'] in scopus_id_dict:
                author_scopus_id = scopus_id_dict[author['orcid']]
                preferred_name = preferred_name_dict[author['orcid']] 
                scopus_link = author_link_dict[author['orcid']]
            else:
                author_scopus_id, preferred_name, scopus_link = scopus.get_scopus_info_from_orcid(author['orcid'])
        
            # If no preferred name is returned, use the author's name as their preferred name
            if len(preferred_name) == 0:
                preferred_name = author['name']

            # If the author has no affiliation, create or update a node for them in the database using their ORCID and/or Scopus ID
            # Otherwise, also set their affiliation
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
    # After processing all authors, print
    print("Author nodes added")
        

def create_project_nodes(tx, projects):
    """
    This function is used to create project nodes in a Neo4j database. It goes through each project, 
    fetches its title, year of creation, and description, and then creates a new node in the database 
    for each project.

    Parameters:
    tx (neo4j.Session): A Neo4j session for running Cypher commands.
    projects (list): A list of projects, where each project is a dictionary with 'id', 'title', 'created_at', 
                     and 'description' keys.
    """
    # Iterate over each project in the list
    for project in projects:
        # Create a new project node in the database with the project's ID, title, creation year, and description
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
    """
    This function is used to create software nodes in a Neo4j database. It goes through each software, 
    fetches its DOI, brand name, year of creation, and description, and then creates a new node in the database 
    for each software.

    Parameters:
    tx (neo4j.Session): A Neo4j session for running Cypher commands.
    softwares (list): A list of softwares, where each software is a dictionary with 'id', 'concept_doi', 
                      'brand_name', 'created_at', and 'description' keys.
    """
    # Iterate over each software in the list
    for software in softwares:

        # Create a new software node in the database with the software's ID, DOI, brand name, creation year, 
        # and description
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

def create_author_project_edge(tx, authors, scopus_id_dict, preferred_name_dict):
    """
    This function creates relationships between authors and projects in the Neo4j graph database.
    For each author, it checks if their ORCID id exists in the Scopus id dictionary.

    Parameters:
    tx (neo4j.Session): A Neo4j session for running Cypher commands.
    authors (list): A list of authors, each represented as a dictionary.
    scopus_id_dict (dict): A dictionary mapping authors' ORCID ids to their Scopus ids.
    preferred_name_dict (dict): A dictionary mapping authors' ORCID ids to their preferred names.
    """
    for author in authors:
        # Check if the author's ORCID is present in the Scopus id dictionary.
        # If it is present, get the Scopus id and the preferred name for the author.
        if author['orcid'] in scopus_id_dict:
            author_scopus_id = scopus_id_dict[author['orcid']]
            preferred_name = preferred_name_dict[author['orcid']] 
        # If not present, get the Scopus id, preferred name and Scopus link using the author's ORCID.
        else:
            author_scopus_id, preferred_name, scopus_link = scopus.get_scopus_info_from_orcid(author['orcid'])

        # If the preferred name is empty, use the author's name.
        if len(preferred_name) == 0:
            preferred_name = author['name']

        # Execute a Cypher command to create a relationship between the author and the project
        # If the author Scopus id is empty, match the author node using the ORCID id
        # If not, match using the Scopus id.
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


def create_author_software_edge(tx, contributors, scopus_id_dict, preferred_name_dict):
    """
    This function is used to create edges between authors (contributors) and software in a Neo4j database. 
    It iterates over each author (contributor) and links them to their respective software.

    Parameters:
    tx (neo4j.Session): A Neo4j session for running Cypher commands.
    contributors (list): A list of authors (contributors), each represented as a dictionary.
    scopus_id_dict (dict): A dictionary mapping authors' (contributors') ORCID ids to their Scopus ids.
    preferred_name_dict (dict): A dictionary mapping authors' (contributors') ORCID ids to their preferred names.
    """
    for contributor in contributors:
        # Check if the contributor's ORCID is in the Scopus id dictionary.
        # If it is, fetch the corresponding Scopus id and preferred name.
        if contributor['orcid'] in scopus_id_dict:
            contributor_scopus_id = scopus_id_dict[contributor['orcid']]
            preferred_name = preferred_name_dict[contributor['orcid']] 
        # If the ORCID is not in the dictionary, get the Scopus id, preferred name, and Scopus link using the ORCID.
        else:
            contributor_scopus_id, preferred_name, scopus_link = scopus.get_scopus_info_from_orcid(contributor['orcid'])
              
        # If the preferred name is empty, use the contributor's name.
        if len(preferred_name) == 0:
            preferred_name = contributor['name']

        # If the Scopus id is empty, match the contributor node using the ORCID id. 
        # Else, match using the Scopus id.
        # In either case, create a relationship between the contributor and the software.
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