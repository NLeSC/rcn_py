import sqlite3
import sys
import pandas as pd
from rcn_py import database
from neo4j import GraphDatabase


file_subject = [("medicine", "Medicine"),
                ("bioc", "Biochemistry, Genetics and Molecular Biology"),
                ("social", "Social Sciences"),
                ("engineer", "Engineering"),
                ("physics", "Physics and Astronomy"),
                ("cs", "Computer Science"),
                ("env", "Environmental Science"),
                ("agricultural", "Agricultural and Biological Sciences"),
                ("earth", "Earth and Planetary Sciences"),
                ("chemistry", "Chemistry"),
                ("psychology", "Psychology"),
                ("neuroscience", "Neuroscience"),
                ("math", "Mathematics"),
                ("immunology", "Immunology and Microbiology"),
                ("materials", "Materials Science"),
                ("multi", "Multidisciplinary"),
                ("arts", "Arts and Humanities"),
                ("chemicalEngineering", "Chemical Engineering"),
                ("pharmacology", "Pharmacology, Toxicology and Pharmaceutics"),
                ("business", "Business, Management and Accounting"),
                ("energy", "Energy"),
                ("nursing", "Nursing"),
                ("eco", "Economics, Econometrics and Finance"),
                ("health", "Health Professions"),
                ("decision", "Decision Sciences"),
                ("veterinary", "Veterinary"),
                ("dentistry", "Dentistry")
                ]


def neo4j_create_people(tx, df, subject):
    for i in range(len(df)):
        # remove noise data
        if not isinstance(df['Author(s) ID'][i], str):
            continue
        author_scopus_id = df["Author(s) ID"][i].split(";")[0:-1]

        # remove papers with single author
        if len(author_scopus_id) < 2:
            continue
        year = df.Year[i]
        author_name = df["Authors"][i].split(", ")[0:len(author_scopus_id)]
        author_aff = df['Authors with affiliations'][i].split("; ")[0:len(author_scopus_id)]
        author_country = [aff.split(", ")[-1] for aff in author_aff]
        if not isinstance(df['Author Keywords'][i], str):
            keywords = []
        else:
            keywords = df["Author Keywords"][i].split("; ")

        # APOC plugin should be installed in your Neo4j Server
        # Create people nodes
        for n in range(len(author_scopus_id)):
            # if the person exists, append keywords and year
            # avoid adding duplicate years
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
        year = df.Year[i]
        cited = df["Cited by"][i]
        # subject = subject
        if not isinstance(df['Author Keywords'][i], str):
            keywords = []
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
        year = df.Year[i]
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
            


# input the scopus csv filepath, and its main subject
# and Neo4j driver uri, username and password
def execution(filepath, subject, uri, user, password):
    # Execution
    df = pd.read_csv(filepath)
    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        driver.verify_connectivity()
        with driver.session(database="neo4j") as session:
            # Create nodes & edges
            session.execute_write(neo4j_create_people, df, subject) 
            session.execute_write(neo4j_create_publication, df, subject)
            session.execute_write(neo4j_create_author_pub_edge, df)
             

# if __name__ == "__main__":