

# Add constraint for Person nodes and Publication nodes
def add_constraint(tx):
    """
    This function is used to add constraints to the nodes in a Neo4j database. 
    It ensures that the 'doi' property of Publication nodes and the 'scopus_id' property of Person nodes are unique.
    """

    # This Cypher command creates a unique constraint on the 'doi' property of Publication nodes.
    # If a constraint by the name 'pub_doi' does not exist, it will be created.
    tx.run("""
            CREATE CONSTRAINT pub_doi IF NOT EXISTS
            FOR (p:Publication) REQUIRE p.doi IS UNIQUE
            """)
    # This Cypher command creates a unique constraint on the 'scopus_id' property of Person nodes.
    # If a constraint by the name 'scopus_id' does not exist, it will be created.
    tx.run("""
            CREATE CONSTRAINT scopus_id IF NOT EXISTS
            FOR (n:Person) REQUIRE n.scopus_id IS UNIQUE
            """)



def neo4j_create_people(tx, df, subject):
    """
    This function is used to create nodes for people in a Neo4j database. 
    It iterates over each row of the input DataFrame, parsing and adding necessary information.

    Parameters:
    tx (neo4j.Session): A session object for Neo4j to run Cypher commands.
    df (pandas.DataFrame): A DataFrame containing information about the people to be added.
    subject (str): The subject associated with the people being added.
    """

    # Iterate over each row in the DataFrame
    for i in range(len(df)):
        # Skip rows where 'Author(s) ID' is not a string
        if not isinstance(df['Author(s) ID'][i], str):
            continue
        author_scopus_id = df["Author(s) ID"][i].split(";")[0:-1]

        # Skip rows with less than two authors
        if len(author_scopus_id) < 2:
            continue
        year = int(df.Year[i])
        author_name = df["Authors"][i].split(", ")[0:len(author_scopus_id)]

        # Extract the author's affiliations and country
        author_aff = df['Authors with affiliations'][i].split("; ")[0:len(author_scopus_id)]
        if author_aff[-1] == ".":
            author_aff = ""
            author_country = ""
        else:
            author_country = [aff.split(", ")[-1] for aff in author_aff]
        
        # Extract the author's keywords
        if not isinstance(df['Author Keywords'][i], str):
            if not isinstance(df['Index Keywords'][i], str):
                keywords = []
            else: 
                index_key = df["Index Keywords"][i].split("; ")
                new_index = []
                for k in index_key:
                    if k.count(" ") < 1:
                        new_index.append(k)
                keywords = new_index
        else:
            keywords = df["Author Keywords"][i].split("; ")

        # Iterate over each author in the list of authors
        for n in range(len(author_scopus_id)):
            # If the person exists, append keywords and year
            # Avoid adding duplicate years
            
            # Use the MERGE command to either create a new node or update an existing one
            # Use the apoc.coll.toSet function from the APOC plugin to add new items to a list property without creating duplicates
            
            tx.run("""
                MERGE (p:Person {scopus_id: $id})
                SET p.name = $name,
                    p.affiliation = $affiliation, 
                    p.country = $country,
                    p.keywords = apoc.coll.toSet(coalesce(p.keywords, []) + $keywords),
                    p.year = apoc.coll.toSet(coalesce(p.year, []) + $year),
                    p.subject = apoc.coll.toSet(coalesce(p.subject, []) + $subject)
                """, 
                id = author_scopus_id[n],
                name = author_name[n],
                affiliation = author_aff[n],
                country = author_country[n],
                keywords = keywords,
                year = year,
                subject = subject
                )
        
        

def neo4j_create_publication(tx, df, subject):
    """
    This function is used to create nodes for publications in a Neo4j database. 
    It iterates over each row of the input DataFrame, parsing and adding necessary information.

    Parameters:
    tx (neo4j.Session): A session object for Neo4j to run Cypher commands.
    df (pandas.DataFrame): A DataFrame containing information about the publications to be added.
    subject (str): The subject associated with the publications being added.
    """

    # Iterate over each row in the DataFrame
    for i in range(len(df)):
        # Skip rows where 'Author(s) ID' is not a string
        if not isinstance(df['Author(s) ID'][i], str):
            continue
        author_scopus_id = df["Author(s) ID"][i].split(";")[0:-1]

        # Skip rows with less than two authors
        if len(author_scopus_id) < 2:
            continue

        # Extract necessary publication information
        doi = df.DOI[i]
        title = df.Title[i]
        year = int(df.Year[i])
        cited = df["Cited by"][i]
        
        # Extract the publication's keywords
        if not isinstance(df['Author Keywords'][i], str):
            if not isinstance(df['Index Keywords'][i], str):
                keywords = []
            else: 
                index_key = df["Index Keywords"][i].split("; ")
                new_index = []
                for k in index_key:
                    if k.count(" ") < 1:
                        new_index.append(k)
                keywords = new_index
        else:
            keywords = df["Author Keywords"][i].split("; ")

        # Use the MERGE command to either create a new node or update an existing one
        # Use the apoc.coll.toSet function from the APOC plugin to add new items to a list property without creating duplicates
        tx.run("""
                MERGE (p:Publication {doi: $doi})
                SET p.title = $title,
                    p.year = $year, 
                    p.cited = $cited,
                    p.keywords = $keywords,
                    p.subject = apoc.coll.toSet(coalesce(p.subject, []) + $subject)
                """, 
                doi = doi,
                title = title,
                year = year,
                cited = cited,
                keywords = keywords,
                subject = subject
                )
        
        
        
        
def neo4j_create_author_pub_edge(tx, df):
    """
    This function is used to create edges between authors and publications in a Neo4j database. 
    It iterates over each row of the input DataFrame, creating a relationship for each author-publication pair.

    Parameters:
    tx (neo4j.Session): A session object for Neo4j to run Cypher commands.
    df (pandas.DataFrame): A DataFrame containing information about the publications and authors to be added.
    """
    
    # Iterate over each row in the DataFrame
    for i in range(len(df)):
        # Skip rows where 'Author(s) ID' is not a string
        if not isinstance(df['Author(s) ID'][i], str):
            continue
        author_scopus_id = df["Author(s) ID"][i].split(";")[0:-1]
        # Skip rows with less than two authors
        if len(author_scopus_id) < 2:
            continue     

        # Extract necessary author-publication relationship information
        author_name = df["Authors"][i].split(", ")[0:len(author_scopus_id)]   
        year = int(df.Year[i])
        doi = df.DOI[i]
        title = df.Title[i]

        # For each author-publication pair, create an IS_AUTHOR_OF relationship
        for i in range(len(author_scopus_id)):
            tx.run("""
                    MATCH 
                        (n:Person {scopus_id: $person_id}), 
                        (p:Publication {doi: $doi})
                    MERGE (n)-[r:IS_AUTHOR_OF]->(p)
                    ON CREATE SET 
                        r.year = $year,
                        r.author_name = $author_name,
                        r.title = $title
                    """, 
                    person_id = author_scopus_id[i], 
                    doi = doi, 
                    year = year,
                    author_name = author_name[i],
                    title = title
                    )
            


# Input the scopus csv filepath, and its main subject
# and Neo4j driver uri, username and password

# def execution(filepath, subject, uri, user, password):
#     with GraphDatabase.driver(uri, auth=(user, password)) as driver:
#         driver.verify_connectivity()
#         with driver.session(database="neo4j") as session:
#             # Create nodes & edges
#             if os.path.exists(filepath):
#             # Skipping bad lines (very rare occurrence): 
#             # Replace the following line: df = pd.read_csv(path, on_bad_lines = 'skip')
#                 df = pd.read_csv(filepath)
                    
#                 session.execute_write(neo4j_create_people, df, subject) 
#                 session.execute_write(neo4j_create_publication, df, subject)
#                 session.execute_write(neo4j_create_author_pub_edge, df)
#                 print ("Successfully insert " + subject + " csv file.")  
#             else:
#                 print("Filepath doesn't exist!") 

