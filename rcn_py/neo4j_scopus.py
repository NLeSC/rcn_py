import os
import pandas as pd
from neo4j import GraphDatabase


# Add constraint for author nodes and publication nodes
def add_constraint(tx):
    tx.run("""
            CREATE CONSTRAINT pub_doi IF NOT EXISTS
            FOR (p:Publication) REQUIRE p.doi IS UNIQUE
            """)
    tx.run("""
            CREATE CONSTRAINT scopus_id IF NOT EXISTS
            FOR (n:Person) REQUIRE n.scopus_id IS UNIQUE
            """)



def neo4j_create_people(tx, df, subject):
    for i in range(len(df)):
        # remove noise data
        if not isinstance(df['Author(s) ID'][i], str):
            continue
        author_scopus_id = df["Author(s) ID"][i].split(";")[0:-1]

        # remove papers with single author
        if len(author_scopus_id) < 2:
            continue
        year = int(df.Year[i])
        author_name = df["Authors"][i].split(", ")[0:len(author_scopus_id)]

        # country and affiliation
        author_aff = df['Authors with affiliations'][i].split("; ")[0:len(author_scopus_id)]
        if author_aff[-1] == ".":
            author_aff = ""
            author_country = ""
        else:
            author_country = [aff.split(", ")[-1] for aff in author_aff]
        
        # keywords
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

        # APOC plugin should be installed in your Neo4j Server
        # Create people nodes
        for n in range(len(author_scopus_id)):
            # if the person exists, append keywords and year
            # avoid adding duplicate years
            # orcid, prefername,link = get_orcid_from_scopus(author_scopus_id[n])
            
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
    for i in range(len(df)):
        # remove noise data
        if not isinstance(df['Author(s) ID'][i], str):
            continue
        author_scopus_id = df["Author(s) ID"][i].split(";")[0:-1]
        # remove papers with single author
        if len(author_scopus_id) < 2:
            continue

        doi = df.DOI[i]
        title = df.Title[i]
        year = int(df.Year[i])
        cited = df["Cited by"][i]
        # keywords
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

        # Create publication nodes
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
    for i in range(len(df)):
        # remove noise data
        if not isinstance(df['Author(s) ID'][i], str):
            continue
        author_scopus_id = df["Author(s) ID"][i].split(";")[0:-1]
        # remove papers with single author
        if len(author_scopus_id) < 2:
            continue     

        author_name = df["Authors"][i].split(", ")[0:len(author_scopus_id)]   
        year = int(df.Year[i])
        doi = df.DOI[i]
        title = df.Title[i]
        # APOC plugin should be installed in your Neo4j Server
        # Create edges
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

def execution(filepath, subject, uri, user, password):
    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        driver.verify_connectivity()
        with driver.session(database="neo4j") as session:
            # Create nodes & edges
            if os.path.exists(filepath):
            # Skipping bad lines (very rare occurrence): 
            # Replace the following line: df = pd.read_csv(path, on_bad_lines = 'skip')
                df = pd.read_csv(filepath)
                    
                session.execute_write(neo4j_create_people, df, subject) 
                session.execute_write(neo4j_create_publication, df, subject)
                session.execute_write(neo4j_create_author_pub_edge, df)
                print ("Successfully insert " + subject + " csv file.")  
            else:
                print("Filepath doesn't exist!") 

