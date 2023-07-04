from json import dumps
import logging
import math
import time
import os
import sys
import itertools
from collections import Counter, defaultdict

from flask import (
    Flask,
    g,
    request,
    Response,
    send_from_directory
)
from neo4j import (
    GraphDatabase,
)
from rcn_py import scopus
from rcn_py import orcid as orcid_py
from rcn_py import openalex
from rcn_py import topic_modeling

# uri = "bolt://localhost:7687"
# username = "neo4j"
# password = "zhiningbai"

# app = Flask(__name__, static_url_path="/static/")
# port = os.getenv("PORT", 8081)
# driver = GraphDatabase.driver(uri, auth=(username, password))
uri = sys.argv[1]
username = sys.argv[2]
password = sys.argv[3]

app = Flask(__name__, static_url_path="/static", static_folder='static')
port = os.getenv("PORT", 8081)
driver = GraphDatabase.driver(uri, auth=(username, password))


# driver.session(database="neo4j")
def get_db(database):
    if not hasattr(g, "neo4j_db"):
            g.neo4j_db = driver.session(database=database)
    return g.neo4j_db


@app.teardown_appcontext
def close_db(error):
    if hasattr(g, "neo4j_db"):
        g.neo4j_db.close()


@app.route("/")
def get_index():
    return app.send_static_file("index_v7.html")

'''
Count how many times an author occurs in all the relationships,
which is used to set different sizes of nodes
'''
def get_link_count_of_author(author_nodes, rel_id_record):
    for author in author_nodes:
        link_num = rel_id_record.count(author["id"])
        author["link_num"] = link_num
        if link_num != 0:
            author["radius"] = 5 + math.log(link_num)
    return author_nodes

'''
Count how many times two authors have collaborated,
it is use dto set the width of the link,
which can be seen when hiding the publication nodes 
(so the links become the relationship between author nodes)
'''
def get_link_count_of_rel(relationships):
    pair_info = defaultdict(lambda: {'titles': [], 'dois': []})
    sorted_relationships = []

    for r in relationships:
        pair = tuple(sorted([r['source'], r['target']]))
        sorted_relationships.append(pair)
        pair_info[pair]['titles'].append(r['title'])
        pair_info[pair]['dois'].append(r['doi'])

    counts = Counter(sorted_relationships)

    result = []
    for pair, count in counts.items():
        result.append({
            'source': pair[0],
            'target': pair[1],
            'count': count,
            'title': pair_info[pair]['titles'],
            'doi': pair_info[pair]['dois']
        })

    return result



''' 
Example network, when getting into the 'Scopus' search
get pub-author relationships (default: 2022, "Deep learning")

Returns:
'nodes': All nodes in the network, including 'publication', 'author', 'software', 'project', etc.
'links': Links between publictaion and author, representing the'IS-AUTHOR-OF' relationship.
'coauthor_nodes': Only author nodes.
'coauthor_links': Coauthorship relationships between authors.
'''
@app.route("/graph")
def get_example_graph():
    # Neo4j Cypher search statement
    def work(tx, year, search_query):
        return list(tx.run("""
            MATCH (n:Person)-[:IS_AUTHOR_OF]->(p:Publication {year: $year}) 
            WHERE   $keyword in p.keywords
            RETURN  COLLECT(n.name) AS name, 
                    COLLECT(CASE WHEN (n.scopus_id) IS NOT NULL THEN n.scopus_id ELSE '' END) AS author_scopus_id, 
                    COLLECT(CASE WHEN (n.orcid) IS NOT NULL THEN n.orcid ELSE '' END) AS orcid,
                    COLLECT(CASE WHEN (n.affiliation) IS NOT NULL THEN n.affiliation ELSE '' END) AS affiliation,
                    COLLECT(CASE WHEN (n.country) IS NOT NULL THEN n.country ELSE '' END) AS country,
                    p.title AS title,
                    p.cited AS cited,
                    p.doi AS doi,
                    p.subject AS subject,
                    p.year AS year
            LIMIT $limit
            """,
            year = year,
            keyword = search_query,
            limit = 300
        ))
    
    # Connect to your Neo4j DB and get the search results 
    db = get_db("neo4j")
    results = db.execute_read(work, 2022, "Deep learning")

    nodes = []
    rels = []
    node_records = {}
    nodes_id_in_rel = []
    coauthor_nodes = []
    coauthor_rels = [] 

    i = 0   # 'i' is the id of every node
    for record in results:
        # 'target' and 'source' are the ids of the nodes in one relationship, they make up the link
        target = i
        node_records[record["doi"]] = i

        # If there is no 'citation count' property, then the node size will be the default size
        if not record["cited"]:
            citation_count = 0
            pub_radius = 6 
        elif math.isnan(record["cited"]):
            citation_count = 0
            pub_radius = 6 
        else:
            citation_count = record["cited"]
            pub_radius = 6 + math.log(citation_count)

        nodes.append({"title": record["title"], 
                      "citation_count": citation_count,
                      "doi": record["doi"],
                      "subject": record["subject"],
                      "year": record["year"],
                      "label": "publication", 
                      "id": target,
                      "color": "publication",
                      "radius": pub_radius
                      })
        i += 1

        coauthor_link = []
        temp_source = []
        # For every author of one publication:
        for a in range(len(record["author_scopus_id"])):
            try:
                # If this author is already stored in the 'nodes',
                # Get its id.
                source = node_records[record["author_scopus_id"][a]]
            except KeyError:
                # If this author is new, save the information
                node_records[record["author_scopus_id"][a]] = i
                source = i
                author = {"title": record["name"][a],
                        "scopus_id": record["author_scopus_id"][a],
                        "orcid": record["orcid"][a],
                        "country": record["country"][a],
                        "affiliation": record["affiliation"][a],
                        "label": "author",
                        "id": source,
                        "color": "author"}
                nodes.append(author)
                coauthor_nodes.append(author)
                i += 1

            # Save all the id of the coauthors of the paper in a list
            temp_source.append(source) 

            # Save all the authors in the network in the list
            nodes_id_in_rel.append(source)

            # Author -> Publication relationships
            rels.append({"source": source, "target": target, "doi":record["doi"], "scopus_id": record["author_scopus_id"][a]})

        # Put the author ids in paris to get coauthorship links
        coauthor_link = coauthor_link+list(itertools.combinations(temp_source, 2))
        # Author -> Author relationships
        for l in coauthor_link:
            coauthor_rels.append({"source": l[0], "target": l[1], "doi":record["doi"], "title": record["title"]})

    # Count how many times the node occurs in the network
    nodes = get_link_count_of_author(nodes, nodes_id_in_rel)
    coauthor_nodes = get_link_count_of_author(coauthor_nodes, nodes_id_in_rel)
    # Count how many times two author have collaborated
    coauthor_rels = get_link_count_of_rel(coauthor_rels)

    return Response(dumps({"nodes": nodes, "links": rels, "coauthor_nodes": coauthor_nodes, "coauthor_links": coauthor_rels}),
                mimetype="application/json")
 

 
'''
Indexing: To avoid too much matching time, 
        make sure that you have created indexes on the title 
        and keywords properties of the Publication nodes in Neo4j:
CREATE INDEX FOR (p:Publication) ON (p.title);
CREATE INDEX FOR (p:Publication) ON (p.keywords);

If there is abstract infomation in your Neo4j DB, also create index on the abstract property:
CREATE INDEX FOR (p:Publication) ON (p.abstract);
'''
@app.route('/topic-search')
def get_search_query():
    # Neo4j Cypher search statement
    def work(tx, year, search_query):
        return list(tx.run("""
            MATCH (n:Person)-[:IS_AUTHOR_OF]->(p:Publication) 
            WHERE  ((p.title CONTAINS $keyword)
                    OR (
                        ANY(keyword IN p.keywords WHERE apoc.text.fuzzyMatch(keyword, $keyword) = true)
                    ))
                AND p.year in $year
            RETURN  COLLECT(n.name) AS name, 
                    COLLECT(CASE WHEN (n.scopus_id) IS NOT NULL THEN n.scopus_id ELSE '' END) AS author_scopus_id, 
                    COLLECT(CASE WHEN (n.orcid) IS NOT NULL THEN n.orcid ELSE '' END) AS orcid,
                    COLLECT(CASE WHEN (n.affiliation) IS NOT NULL THEN n.affiliation ELSE '' END) AS affiliation,
                    COLLECT(CASE WHEN (n.country) IS NOT NULL THEN n.country ELSE '' END) AS country,
                    p.title AS title,
                    p.cited AS cited,
                    p.doi AS doi,
                    p.subject AS subject,
                    p.year AS year
            LIMIT $limit
            """,
            year = year,
            keyword = search_query,
            limit = 300
        ))

    try:
        # Get the user input
        year = request.args["year"]
        keyword = request.args["keyword"]
    except KeyError:
        return []
    else:
        # Connect to your Neo4j DB and get the search results 
        db = get_db("neo4j")
        year = list(map(int, year.split(","))) # year list
        query = keyword.replace("+", " ")   # keyword string
        results = db.execute_read(work, year, query)
        
        nodes = []
        rels = []
        node_records = {}
        nodes_id_in_rel = []
        coauthor_nodes = []
        coauthor_rels = [] 
        i = 0   # 'i' is the id of every node

        for record in results:
            # 'target' and 'source' are the ids of the nodes in one relationship, they make up the link
            target = i
            node_records[record["doi"]] = i

            # If there is no 'citation count' property, then the node size will be the default size
            if not record["cited"]:
                citation_count = 0
                pub_radius = 6 
            elif math.isnan(record["cited"]):
                citation_count = 0
                pub_radius = 6 
            else:
                citation_count = record["cited"]
                pub_radius = 6 + math.log(citation_count)

            nodes.append({"title": record["title"], 
                        "citation_count": citation_count,
                        "doi": record["doi"],
                        "subject": record["subject"],
                        "year": record["year"],
                        "label": "publication", 
                        "id": target,
                        "color": "publication",
                        "radius": pub_radius
                        })
            i += 1
            coauthor_link = []
            temp_source = []

            # For every author of one publication:
            for a in range(len(record["name"])):
                try:
                    # If this author is already stored in the 'nodes',
                    # Get its id.
                    source = node_records[record["name"][a]]
                except KeyError:
                    # If this author is new, save the information
                    node_records[record["name"][a]] = i
                    source = i
                    author = {"title": record["name"][a],
                            "scopus_id": record["author_scopus_id"][a],
                            "orcid": record["orcid"][a],
                            "country": record["country"][a],
                            "affiliation": record["affiliation"][a],
                            "label": "author",
                            "id": source,
                            "color": "author"}
                    nodes.append(author)
                    coauthor_nodes.append(author)
                    i += 1

                # Save all the id of the coauthors of the paper in a list
                temp_source.append(source)

                # Save all the authors in the network in the list
                nodes_id_in_rel.append(source)

                # Author -> Publication relationships
                rels.append({"source": source, "target": target, "doi":record["doi"], "scopus_id": record["author_scopus_id"][a]})
        
            # Put the author ids in paris to get coauthorship links
            coauthor_link = coauthor_link+list(itertools.combinations(temp_source, 2))
            # Author -> Author relationships
            for l in coauthor_link:
                coauthor_rels.append({"source": l[0], "target": l[1], "doi":record["doi"], "title": record["title"]})

        # Count how many times the node occurs in the network
        nodes = get_link_count_of_author(nodes, nodes_id_in_rel)
        coauthor_nodes = get_link_count_of_author(coauthor_nodes, nodes_id_in_rel)

        # Count how many times two author have collaborated
        coauthor_rels = get_link_count_of_rel(coauthor_rels)
       
        return Response(dumps({"nodes": nodes, "links": rels, "coauthor_nodes": coauthor_nodes, "coauthor_links": coauthor_rels}),
                    mimetype="application/json")
       

'''
Search for authors using ORCID from Neo4j Scopus DB
'''
@app.route('/author_search')
def author_search():
    # Neo4j Cypher search statement
    def get_coauthor_byID(tx, scopus_id, orcid):
        return list(tx.run("""
            MATCH (n:Person)-[:IS_AUTHOR_OF]->(p)
                    <-[:IS_AUTHOR_OF]-(m:Person)
            WHERE labels(p) IN [['Publication'], ['Project'], ['Software']] AND
                    (n.orcid = $orcid OR n.scopus_id = $scopus_id)
            RETURN  collect(m.name)+apoc.coll.toSet(collect(n.name)) AS name,
                    collect(CASE WHEN (m.scopus_id) IS NOT NULL THEN m.scopus_id ELSE '' END)+apoc.coll.toSet(collect(n.scopus_id)) AS author_scopus_id, 
                    collect(CASE WHEN (m.orcid) IS NOT NULL THEN m.orcid ELSE '' END)+apoc.coll.toSet(collect(n.orcid)) AS author_orcid,
                    collect(CASE WHEN (m.affiliation) IS NOT NULL THEN m.affiliation ELSE '' END)+apoc.coll.toSet(collect(n.affiliation)) AS affiliation,
                    collect(CASE WHEN (m.country) IS NOT NULL THEN m.country ELSE '' END)+apoc.coll.toSet(collect(n.country)) AS country,
                    p.title AS title,
                    p.cited AS cited,
                    p.doi AS doi,
                    p.subject AS subject,
                    p.year AS year,
                    CASE 
                        WHEN labels(p) = ['Project'] THEN  'project'
                        WHEN labels(p) = ['Software'] THEN 'software'
                        WHEN labels(p) = ['Publication'] THEN 'publication'
                        ELSE '' 
                    END AS label
            """,
            scopus_id = scopus_id,
            orcid = orcid
        ))
    
    def get_coauthor_byName(tx, namelist):
        return list(tx.run("""
            MATCH (n:Person)-[:IS_AUTHOR_OF]->(p)
                    <-[:IS_AUTHOR_OF]-(m:Person)
            WHERE labels(p) IN [['Publication'], ['Project'], ['Software']] AND
                    (n.name in $namelist)
            RETURN  
                    collect(m.name)+apoc.coll.toSet(collect(n.name)) AS name,
                    collect(CASE WHEN (m.scopus_id) IS NOT NULL THEN m.scopus_id ELSE '' END)+apoc.coll.toSet(collect(n.scopus_id)) AS author_scopus_id, 
                    collect(CASE WHEN (m.orcid) IS NOT NULL THEN m.orcid ELSE '' END)+apoc.coll.toSet(collect(n.orcid)) AS author_orcid,
                    collect(CASE WHEN (m.affiliation) IS NOT NULL THEN m.affiliation ELSE '' END)+apoc.coll.toSet(collect(n.affiliation)) AS affiliation,
                    collect(CASE WHEN (m.country) IS NOT NULL THEN m.country ELSE '' END)+apoc.coll.toSet(collect(n.country)) AS country,
                    p.title AS title,
                    p.cited AS cited,
                    p.doi AS doi,
                    p.subject AS subject,
                    p.year AS year,
                    CASE 
                        WHEN labels(p) = ['Project'] THEN  'project'
                        WHEN labels(p) = ['Software'] THEN 'software'
                        WHEN labels(p) = ['Publication'] THEN 'publication'
                        ELSE '' 
                    END AS label
            """,
            namelist = namelist
        ))
  
    try:
        orcid = request.args["orcid"]
        firstname = request.args["firstname"]
        surname = request.args["surname"]
        rsd = request.args["rsd"] # If user is in the RSD page, then use RSD database
    except KeyError:
        return []
    else:
        if rsd:
            db = get_db("rsd")
        else:
            db = get_db("neo4j")
        
        # If we have the fullname but no orcid, try to get orcid by fullname first
        if (not orcid) or (firstname and surname):
            orcid = orcid_py.name_to_orcid_id(firstname+' '+surname)
        if orcid:
            # Try to connect to the Scopus data 
            scopus_id = scopus.get_scopus_info_from_orcid(orcid)[0]
            results = db.execute_read(get_coauthor_byID, scopus_id, orcid)

            # OpenAlex profile information
            openalex_search = openalex.search_user_by_orcid(orcid)

            search_author_name = openalex_search["display_name"]
            works_count = openalex_search['works_count']
            cited_by_count = openalex_search['cited_by_count']
            h_index = openalex_search['summary_stats']['h_index']
            ror = openalex_search['last_known_institution']['ror']
            search_aff_name = openalex_search['last_known_institution']['display_name']
            search_country = openalex_search['last_known_institution']['country_code']
            cite_by_year = openalex_search['counts_by_year']
            concept_score = {}
            concept_score['concept_name'] = []
            concept_score['score'] = []
            for c in openalex_search['x_concepts'][0:7]:
                concept_score['concept_name'].append(c['display_name'])
                concept_score['score'].append(c['score'])

        # If all the attampt above failed, use the author's name.
        elif firstname and surname:
            namelist = []
            namelist.append(firstname + ' ' + surname)
            namelist.append(surname + ' ' + firstname[0]+ ".")
            namelist.append(firstname[0]+ ". "+surname)
            results = db.execute_read(get_coauthor_byName, namelist)       
        else:
            return []
        
        # Start generating the nodes and links list in the network
        nodes = []
        rels = []
        node_records = {}
        nodes_id_in_rel = []
        i = 0
        coauthor_nodes = []
        coauthor_rels = [] 

        for record in results:
            target = i
            node_records[record['doi']] = i

            # If there is no 'citation count' property, then the node size will be the default size
            if not record["cited"]:
                citation_count = 0
                pub_radius = 6 
            elif math.isnan(record["cited"]):
                citation_count = 0
                pub_radius = 6 
            else:
                citation_count = record["cited"]
                pub_radius = 6 + math.log(citation_count)

            nodes.append({"title": record["title"], 
                        "citation_count": citation_count,
                        "doi": record["doi"],
                        "subject": record["subject"],
                        "year": record["year"],
                        "label": record["label"], 
                        "id": target,
                        "color": record["label"],
                        "radius": pub_radius
                        })
            i += 1
            temp_source = []
            coauthor_link = []
            # For every author of one publication:
            for index in range(len(record["name"])):
                    # If there is a new author, save the information
                    name = record["name"][index]
                    country = record["country"][index]
                    aff = record["affiliation"][index]

                    # If the author node is exactly who we are searching for, set it a different color
                    if (record["author_scopus_id"][index] == scopus_id and record["author_scopus_id"][index]) or (record["author_orcid"][index] == orcid and record["author_orcid"][index]):
                        author_color = "author_highlight"
                    else:
                        # Others will be the first-layer coauthor
                        author_color = "first_coauthor"

                    try:
                        if len(record["author_orcid"][index]) != 0:
                            source = node_records[record["author_orcid"][index]]
                        elif len(record["author_scopus_id"][index]) != 0:
                            source = node_records[record["author_scopus_id"][index]]
                        else:
                            source = node_records[name]
                       
                    except KeyError:
                        # Save the most unique feature into the record list.
                        if len(record["author_orcid"][index]) != 0:
                            node_records[record["author_orcid"][index]] = i
                        elif len(record["author_scopus_id"][index]) != 0:
                            node_records[record["author_scopus_id"][index]] = i
                        else:
                            node_records[name] = i
                        
                        source = i
                        author = {"title": name,
                                "scopus_id": record["author_scopus_id"][index],
                                "orcid": record["author_orcid"][index],
                                "country": country,
                                "affiliation": aff,
                                "label": "author",
                                "id": source,
                                "color": author_color}
                        nodes.append(author)
                        coauthor_nodes.append(author)
                        i += 1

                    # Save all the id of the coauthors of the paper in a list 
                    temp_source.append(source)
                    # Save all the authors in the network in the list
                    nodes_id_in_rel.append(source)
                    # Author -> Publication relationships
                    rels.append({"source": source, "target": target, "doi":record["doi"], 
                                 "scopus_id": record["author_scopus_id"][index],
                                 "orcid": record["author_orcid"][index]})
                    
            # Put the author ids in paris to get coauthorship links
            coauthor_link = coauthor_link+list(itertools.combinations(temp_source, 2))
            # Author -> Author relationships
            for l in coauthor_link:
                coauthor_rels.append({"source": l[0], "target": l[1], "doi":record["doi"], "title": record["title"]})

        # Count how many times the node occurs in the network
        nodes = get_link_count_of_author(nodes, nodes_id_in_rel)
        coauthor_nodes = get_link_count_of_author(coauthor_nodes, nodes_id_in_rel)
        # Count how many times two author have collaborated
        coauthor_rels = get_link_count_of_rel(coauthor_rels)
            
        return Response(dumps({"nodes": nodes, "links": rels, "coauthor_nodes": coauthor_nodes, "coauthor_links": coauthor_rels,
                               "search_author_name": search_author_name, "works_count": works_count,"cited_by_count": cited_by_count,
                               "h_index": h_index, "ror": ror, "search_aff_name": search_aff_name, "search_country":search_country,
                               "cite_by_year": cite_by_year, "concept_score": concept_score}),
                    mimetype="application/json")



# ################################ Publication DOI search ################################
'''
Use DOI to search for publications
'''
@app.route('/pub_search')
def get_pub_search():
    def doi_search(tx, doi):
        return list(tx.run("""
            MATCH (n:Person)-[:IS_AUTHOR_OF]->(p {doi: $doi})
            RETURN  
                    COLLECT(n.name) AS name, 
                    COLLECT(CASE WHEN (n.scopus_id) IS NOT NULL THEN n.scopus_id ELSE '' END) AS author_scopus_id, 
                    COLLECT(CASE WHEN (n.orcid) IS NOT NULL THEN n.orcid ELSE '' END) AS orcid,
                    COLLECT(CASE WHEN (n.affiliation) IS NOT NULL THEN n.affiliation ELSE '' END) AS affiliation,
                    COLLECT(CASE WHEN (n.country) IS NOT NULL THEN n.country ELSE '' END) AS country,
                    p.title AS title,
                    p.cited AS cited,
                    p.subject AS subject,
                    p.year AS year,
                    CASE 
                        WHEN labels(p) = ['Project'] THEN  'project'
                        WHEN labels(p) = ['Software'] THEN 'software'
                        WHEN labels(p) = ['Publication'] THEN 'publication'
                        ELSE '' 
                    END AS label
            """,
            doi = doi
        ))
    
    try:
        doi = request.args["doi"]

    except KeyError:
        return []
    else:
        if "https://doi.org/" in doi:
            doi = doi.replace("https://doi.org/",'')

        # Openalex profile information
        openalex_pub_result = openalex.get_pub_info_by_doi(doi)
        if openalex_pub_result['meta']['count'] != 0:
            author_list = []
            orcid_list = []
            concept_score = {}
            concept_score['concept_name'] = []
            concept_score['score'] = []
            openalex_pub_result = openalex.get_pub_info_by_doi(doi)
            title = openalex_pub_result['results'][0]["title"]
            for au in openalex_pub_result['results'][0]["authorships"]:
                author_list.append(au['author']['display_name'])
                orcid_list.append(au['author']['orcid'])
            author_string = ', '.join(author_list)
            date = openalex_pub_result['results'][0]['publication_date']
            source = openalex_pub_result['results'][0]['primary_location']["source"]
            if source['issn_l']:
                source_issn = source["display_name"]+', '+ source['issn_l']
            else:
                source_issn = source["display_name"]
            cited_by_count = openalex_pub_result['results'][0]["cited_by_count"]
            concepts = openalex_pub_result['results'][0]['concepts']
            for c in concepts[0:7]:
                concept_score['concept_name'].append(c['display_name'])
                concept_score['score'].append(c['score'])
            cite_by_year = openalex_pub_result['results'][0]['counts_by_year']
            openalex_data = True
        else:
            openalex_data = False

        # Start generating nodes and links in the network
        db = get_db("neo4j")
        results = db.execute_read(doi_search, doi)
        
        nodes = []
        rels = []
        i = 0
        coauthor_nodes = []
        coauthor_rels = [] 

        # Get the first result
        if results:
            record = results[0]
        else:
            return 
        
        target = i

        # If there is no 'citation count' property, then the node size will be the default size
        if record["cited"]:
            if math.isnan(record["cited"]):
                citation_count = 0
                pub_radius = 6
            else:
                citation_count = record["cited"]
                pub_radius = 6 + math.log(citation_count)
        else:
            citation_count = 0
            pub_radius = 6

        nodes.append({"title": record["title"], 
                        "citation_count": citation_count,
                        "doi": doi,
                        "subject": record["subject"],
                        "year": record["year"],
                        "label": record["label"], 
                        "id": target,
                        "color": record["label"],
                        "radius": pub_radius})
        i += 1
        temp_source = []
        coauthor_link = []

        # For every author of one publication:
        for a in range(len(record["author_scopus_id"])):
            source = i

            author = {"title": record["name"][a],
                        "scopus_id": record["author_scopus_id"][a],
                        "orcid": record["orcid"][a],
                        "country": record["country"][a],
                        "affiliation": record["affiliation"][a],
                        "label": "author",
                        "id": source,
                        "color": "author",
                        "radius": 5
                        }
            nodes.append(author)
            coauthor_nodes.append(author)

            # Save all the id of the coauthors of the paper in a list 
            temp_source.append(source)
            i += 1

            # Author -> Publication relationships
            rels.append({"source": source, "target": target, "doi":doi, "scopus_id": record["author_scopus_id"][a]})

        # Put the author ids in paris to get coauthorship links
        coauthor_link = coauthor_link+list(itertools.combinations(temp_source, 2))
        # Author -> Author relationships
        for l in coauthor_link:
            coauthor_rels.append({"source": l[0], "target": l[1], "count": 1,"doi":doi, "title": record["title"]})

    # If there is return data from OpenAlex, then make the profile, if else, then only show the network
    if openalex_data:
        return Response(dumps({"nodes": nodes, "links": rels, "coauthor_nodes": coauthor_nodes, "coauthor_links": coauthor_rels,
                           "title": title, 'doi': doi, 'author_string': author_string, 'author_list':author_list,
                           'orcid_list':orcid_list, 'date': date, 'source_issn':source_issn,
                           'cited_by_count':cited_by_count, 'concept_score': concept_score, 'cite_by_year':cite_by_year}),
                    mimetype="application/json")
    else:
        return Response(dumps({"nodes": nodes, "links": rels, "coauthor_nodes": coauthor_nodes, "coauthor_links": coauthor_rels}),
                    mimetype="application/json")


# ################################ Expand the network ################################
'''
Get all the nodes and links connected by a node from the database.
There are several scenario: 
If the node is an author: get all the works of the author
If the node is a research work (publication/software/project), get all the authors of this work
'''
@app.route('/show_link')
def show_link():
    def person_node(tx, unique_id):
        return list(tx.run("""
            MATCH (n:Person)-[r]->(p) 
            WHERE labels(p) IN [['Publication'], ['Project'], ['Software']] AND
                    (n.orcid = $orcid OR n.scopus_id = $scopus_id)
            RETURN  p.title AS title,
                    p.cited AS cited,
                    p.doi AS doi,
                    p.subject AS subject,
                    p.year AS year,
                    CASE 
                        WHEN labels(p) = ['Project'] THEN  'project'
                        WHEN labels(p) = ['Software'] THEN 'software'
                        WHEN labels(p) = ['Publication'] THEN 'publication'
                        ELSE '' 
                    END AS label
            LIMIT $limit
            """,
            scopus_id = unique_id,
            orcid = unique_id,
            limit = 50
        ))
    def pub_node(tx, doi):
        return list(tx.run("""
            MATCH (p:Publication {doi: $doi})<-[r]-(n) 
            RETURN  n.scopus_id AS scopus_id,
                    n.name AS name,
                    n.country AS country,
                    n.affiliation AS affiliation
            LIMIT $limit
            """,
            doi = doi,
            limit = 50
        ))
    def project_node(tx, project_id):
        return list(tx.run("""
            MATCH (p:Project {project_id: $project_id})<-[r]-(n) 
            RETURN  n.orcid AS orcid,
                    n.scopus_id AS scopus_id,
                    n.name AS name,
                    n.country AS country,
                    n.affiliation AS affiliation
            LIMIT $limit
            """,
            project_id = project_id,
            limit = 50
        ))
    def software_node(tx, software_id):
        return list(tx.run("""
            MATCH (p:Software {software_id: $software_id})<-[r]-(n) 
            RETURN  n.orcid AS orcid,
                    n.scopus_id AS scopus_id,
                    n.name AS name,
                    n.country AS country,
                    n.affiliation AS affiliation
            LIMIT $limit
            """,
            software_id = software_id,
            limit = 50
        ))

    try:
        # This is the constriant property in Neo4j (author:scopus_id, pub:doi)
        unique_id = request.args["unique_id"]
        # Determine whether it is author or pub node
        node_label = request.args["label"]
        # Id of the selected node
        node_id = int(request.args["node_id"])
        # The number of nodes in the network, new source and target will be added from maxId
        max_id = int(request.args["maxId"])
        # Get all existing nodes that connect to the selected node
        linkList = request.args["linkList"]
        # Get coauthor ids 
        coauthorID = request.args["coauthorList"]
    except KeyError:
        return []
    else:
        nodes = []
        rels = []
        coauthor_nodes = []
        coauthor_rels = []
        link_list = linkList.split(',')
        coauthorID = coauthorID.split(',')
        if len(coauthorID) != 0:
            coauthorID= list(map(int, coauthorID))

        db = get_db("neo4j")

        # Publication, then create new author nodes
        if node_label == "publication":
            results = db.execute_read(pub_node, unique_id)
            coauthor_link = []
            for record in results:
                if record['scopus_id'] not in link_list:
                    max_id += 1
                    author = {"title": record['name'],
                            "scopus_id": record['scopus_id'],
                            "country": record['country'],
                            "affiliation": record['affiliation'],
                            "label": "author",
                            "id": max_id,
                            "color": "author",
                            "link_num": 1,
                            "radius": 5}
                    nodes.append(author)
                    coauthorID.append(max_id)
                    rels.append({"source": max_id, "target": node_id, "doi": unique_id, "scopus_id": record['scopus_id']})
            coauthor_link = coauthor_link+list(itertools.combinations(coauthorID, 2))
            for l in coauthor_link:
                coauthor_rels.append({"source": l[0], "target": l[1], "count": 1, "doi":unique_id})
            coauthor_nodes = nodes
            
        # Author, then create new publication/software/project nodes
        if node_label == "author":
            if "https://orcid.org/" in unique_id:
                unique_id = unique_id.replace("https://orcid.org/",'')
            results = db.execute_read(person_node, unique_id)
            for record in results:
                if record['doi'] not in link_list:
                    # if record["cited"]:
                    if record["cited"]:
                        if math.isnan(record["cited"]):
                            citation_count = 0
                            pub_radius = 6
                        else:
                            citation_count = record["cited"]
                            pub_radius = 6 + math.log(citation_count)
                    else:
                        citation_count = 0
                        pub_radius = 6
                    # else:
                    #     citation_count = 0
                    #     pub_radius = 6
                    max_id += 1
                    nodes.append({"title": record["title"], 
                        "citation_count": citation_count,
                        "doi": record["doi"],
                        "subject": record["subject"],
                        "year": record["year"],
                        "label": record['label'], 
                        "id": max_id,
                        "color": record['label'],
                        "radius": pub_radius})
                    rels.append({"source": node_id, "target": max_id, "doi": record["doi"], "scopus_id": unique_id})

        # Project/Software
        if node_label == "project" or node_label == "software":
            if node_label == "project":
                results = db.execute_read(project_node, unique_id)
            if node_label == "software":
                results = db.execute_read(software_node, unique_id)
            coauthor_link = []
            for record in results:
                if record['orcid'] not in link_list:
                    max_id += 1
                    author = {"title": record['name'],
                            "scopus_id": record['scopus_id'],
                            "orcid": record['orcid'],
                            "country": record['country'],
                            "affiliation": record['affiliation'],
                            "label": "author",
                            "id": max_id,
                            "color": "author",
                            "link_num": 1,
                            "radius": 5}
                    nodes.append(author)
                    coauthorID.append(max_id)
                    rels.append({"source": max_id, "target": node_id, "id": unique_id, "orcid": record['orcid']})

            # Put the author ids in paris to get coauthorship links
            coauthor_link = coauthor_link+list(itertools.combinations(coauthorID, 2))
            # Author -> Author relationship
            for l in coauthor_link:
                coauthor_rels.append({"source": l[0], "target": l[1], "count": 1, "id": unique_id})
            coauthor_nodes = nodes

        return Response(dumps({"nodes": nodes, "links": rels, "coauthor_nodes": coauthor_nodes, "coauthor_links": coauthor_rels}),
                    mimetype="application/json")
    

# #################################### eScience #########################################
# This is an initial network for RSD, that only contains the nodes and links from eScience

@app.route("/escience")
def show_esc_graph():
    def work(tx):
        return list(tx.run("""
            MATCH (n:Person)-[:IS_AUTHOR_OF]->(p)
            WHERE   labels(p) IN [['Publication'], ['Project'], ['Software']] AND
                    n.affiliation = "Netherlands eScience Center"
            RETURN  COLLECT(n.name) AS name_list, 
                    COLLECT(CASE WHEN (n.scopus_id) IS NOT NULL THEN n.scopus_id ELSE '' END) AS scopus_id, 
                    COLLECT(CASE WHEN (n.orcid) IS NOT NULL THEN n.orcid ELSE '' END) AS orcid,
                    COLLECT(CASE WHEN (n.affiliation) IS NOT NULL THEN n.affiliation ELSE '' END) AS affiliation,
                    COLLECT(CASE WHEN (n.country) IS NOT NULL THEN n.country ELSE '' END) AS country,
                    p.title AS title,
                    p.cited AS cited,
                    p.doi AS doi,
                    p.subject AS subject,
                    p.year AS year,
                    p.project_id AS project_id,
                    p.software_id AS software_id,
                    p.description AS description,
                    CASE 
                        WHEN labels(p) = ['Project'] THEN  'project'
                        WHEN labels(p) = ['Software'] THEN 'software'
                        WHEN labels(p) = ['Publication'] THEN 'publication'
                        ELSE '' 
                    END AS label
            """
        ))
        
    db = get_db("rsd")
    results = db.execute_read(work)

    nodes = []
    rels = []
    node_records = {}
    nodes_id_in_rel = []

    coauthor_nodes = []
    coauthor_rels = [] 
        
    
    i = 0
    # For every work in the results
    for record in results:
        target = i
        node_records[record["doi"]] = i

        # If there is no 'citation count' property, then the node size will be the default size
        if record["cited"]:
            if math.isnan(record["cited"]):
                citation_count = 0
                pub_radius = 6
            else:
                citation_count = record["cited"]
                pub_radius = 6 + math.log(citation_count)
        else:
            citation_count = 0
            pub_radius = 6

        nodes.append({"title": record["title"], 
                      "citation_count": citation_count,
                      "doi": record["doi"],
                      "project_id": record["project_id"],
                      "software_id": record["software_id"],
                      "subject": record["subject"],
                      "year": record["year"],
                      "label": record["label"], 
                      "id": target,
                      "color": record["label"],
                      "radius": pub_radius
                      })
        i += 1

        # if the work is publication, then use scopus id
        coauthor_link = []
        temp_source = []
        
        for n in range(len(record["name_list"])):
            
            try:
                if len(record["scopus_id"][n]) != 0:
                    source = node_records[record["scopus_id"][n]]
                elif len(record["orcid"][n]) != 0:
                    source = node_records[record["orcid"][n]]
                else:
                    continue
            except KeyError:
                if len(record["scopus_id"][n]) != 0:
                    node_records[record["scopus_id"][n]] = i
                elif len(record["scopus_id"][n]) != 0:
                    node_records[record["orcid"][n]] = i
                else:
                    continue
                source = i

                author = {"title": record["name_list"][n],
                            "scopus_id": record["scopus_id"][n],
                            "orcid": record["orcid"][n],
                            "country": record["country"][n],
                            "affiliation": record["affiliation"][n],
                            "label": "author",
                            "id": source,
                            "color": "author"}
                nodes.append(author)
                coauthor_nodes.append(author)
                i += 1

            # Save all the id of the coauthors of the paper in a list
            temp_source.append(source)
            nodes_id_in_rel.append(source)
            # Author -> Publication relationships
            rels.append({"source": source, "target": target, "doi":record["doi"], "scopus_id": record["scopus_id"][n], "orcid":record["orcid"][n]})

        # Put the author ids in paris to get coauthorship links
        coauthor_link = coauthor_link+list(itertools.combinations(temp_source, 2))
        # Author -> Author relationships
        for l in coauthor_link:
            coauthor_rels.append({"source": l[0], "target": l[1], "doi":record["doi"], "title": record["title"]})

    # Count how many times the node occurs in the network
    nodes = get_link_count_of_author(nodes, nodes_id_in_rel)
    coauthor_nodes = get_link_count_of_author(coauthor_nodes, nodes_id_in_rel)
    # Count how many times two author have collaborated
    coauthor_rels = get_link_count_of_rel(coauthor_rels)
        
    return Response(dumps({"nodes": nodes, "links": rels, 
                           "coauthor_nodes": coauthor_nodes, "coauthor_links": coauthor_rels}),
                    mimetype="application/json")



################################## OpenAlex affiliation ####################################
'''
Openalex search, only use OpenAlex API
'''
@app.route("/openalex-aff-search")
def openalex_aff_search():
    try:
        aff_name = request.args["aff_name"]
        start_year = request.args["start_year"]
        end_year = request.args["end_year"]
    except KeyError:
        return []
    else:
        aff_result = openalex.find_institution(aff_name)
        # if fetch no info
        if aff_result['meta']['count'] == 0:
            return []
        
        aff_info = aff_result['results'][0]

        display_name = aff_info['display_name']
        ror = aff_info['ror']

        works_count = aff_info['works_count']
        cite_count = aff_info['cited_by_count']
        h_index = aff_info['summary_stats']['h_index']
        
        home_page = aff_info['homepage_url']
        city = aff_info['geo']['city']
        country = aff_info['geo']['country']
        counts_by_year = aff_info['counts_by_year']
        concept_score = {}
        concept_score['concept_name'] = []
        concept_score['score'] = []
        for c in aff_info['x_concepts'][0:7]:
                concept_score['concept_name'].append(c['display_name'])
                concept_score['score'].append(c['score'])

        # Get works
        works = openalex.get_works_of_one_institution_by_year(aff_name, start_year, end_year)
        topic_names, openalex_aff_works = topic_modeling.openalex_build_corpus(works, 5)

        i = 0
        node_records = {}
        nodes = []
        rels = []
        nodes_id_in_rel = []
        coauthor_nodes = []
        coauthor_rels = [] 

        for work in openalex_aff_works:

            if not work["title"]:
                continue

            target = i
            node_records[work["doi"]] = i
            if math.isnan(work["cited_by_count"]) or work["cited_by_count"] == 0 :
                citation_count = 0
                pub_radius = 6
            else:
                citation_count = work["cited_by_count"]
                pub_radius = 6 + math.log(citation_count)

            nodes.append({"title": work["title"], 
                        "citation_count": citation_count,
                        "doi": work["doi"],
                        "openalex_id": work["id"],
                        "year": work['publication_year'],
                        "label": 'publication', 
                        "id": target,
                        "color": 'publication',
                        "radius": pub_radius,
                        "group": work["group_id"],
                        "topic_name": work['topic_name']
                        })
            i += 1

            # if pub, then use scopus id
            coauthor_link = []
            temp_source = []
            
            for au in work['authorships']:
                # if not au['author']['display_name']:
                #     continue
                try:
                    source = node_records[au['author']['display_name']]
                    
                except KeyError:
                    if 'display_name' not in au['author']:
                        continue
                   
                    node_records[au['author']['display_name']] = i
                    source = i

                    # handle empty values
                    if len(au['institutions']) == 0:
                        country_code = ''
                        affiliation_name = ''
                    else:
                        country_code = au['institutions'][0]['country_code']
                        affiliation_name = au['institutions'][0]['display_name']

                    author = {
                                "title": au['author']['display_name'],
                                "orcid": au['author']["orcid"],
                                "openalex_id": au['author']['id'],
                                "country": country_code,
                                "affiliation": affiliation_name,
                                "label": "author",
                                "id": source,
                                "color": "author"}
                    nodes.append(author)
                    coauthor_nodes.append(author)
                    i += 1
                temp_source.append(source)
                nodes_id_in_rel.append(source)
                rels.append({"source": source, "target": target, "doi":work["doi"], "author_name":au['author']['display_name']})

            coauthor_link = coauthor_link+list(itertools.combinations(temp_source, 2))

            for l in coauthor_link:
                coauthor_rels.append({"source": l[0], "target": l[1], "doi":work["doi"], "title": work["title"]})

        nodes = get_link_count_of_author(nodes, nodes_id_in_rel)
        coauthor_nodes = get_link_count_of_author(coauthor_nodes, nodes_id_in_rel)
        coauthor_rels = get_link_count_of_rel(coauthor_rels)
        
        return Response(dumps({"nodes": nodes, "links": rels, "coauthor_nodes": coauthor_nodes, "coauthor_links": coauthor_rels,
                               "aff_name": display_name, 'ror': ror, 'works_count': works_count, 'cited_by_count':cite_count,
                               'h_index': h_index, 'home_page': home_page, 'city': city, 'country': country,
                               'concept_score': concept_score, 'cite_by_year': counts_by_year, "topic_names": topic_names
                               }),
                    mimetype="application/json")
    
'''
Only get the profile information 
'''
@app.route("/openalex-aff-search-profile-info")
def openalex_aff_search_profile_info():
    try:
        aff_name = request.args["aff_name"]
    except KeyError:
        return []
    else:
        aff_result = openalex.find_institution(aff_name)
        # if fetch no info
        if aff_result['meta']['count'] == 0:
            return []
        
        aff_info = aff_result['results'][0]

        display_name = aff_info['display_name']
        ror = aff_info['ror']

        works_count = aff_info['works_count']
        cite_count = aff_info['cited_by_count']
        h_index = aff_info['summary_stats']['h_index']
        
        home_page = aff_info['homepage_url']
        city = aff_info['geo']['city']
        country = aff_info['geo']['country']
        counts_by_year = aff_info['counts_by_year']
        concept_score = {}
        concept_score['concept_name'] = []
        concept_score['score'] = []
        for c in aff_info['x_concepts'][0:7]:
                concept_score['concept_name'].append(c['display_name'])
                concept_score['score'].append(c['score'])
        
        return Response(dumps({"aff_name": display_name, 'ror': ror, 'works_count': works_count, 'cited_by_count':cite_count,
                               'h_index':h_index, 'home_page': home_page, 'city':city, 'country':country,
                               'concept_score': concept_score, 'cite_by_year':counts_by_year
                               }),
                    mimetype="application/json")
    
'''
Only get the network data (without the profile information)
'''
@app.route("/openalex-aff-search-without-profile")
def openalex_aff_search_without_profile_info():
    try:
        aff_name = request.args["aff_name"]
        pub_size = int(request.args["size"])
    except KeyError:
        return []
    else:
        # Get works
        openalex_aff_works = openalex.get_works_of_one_institution(aff_name, pub_size)

        i = 0
        node_records = {}
        nodes = []
        rels = []
        nodes_id_in_rel = []
        coauthor_nodes = []
        coauthor_rels = [] 

        for work in openalex_aff_works:
            target = i
            node_records[work["doi"]] = i
            if math.isnan(work["cited_by_count"]) or work["cited_by_count"] == 0 :
                citation_count = 0
                pub_radius = 6
            else:
                citation_count = work["cited_by_count"]
                pub_radius = 6 + math.log(citation_count)

            nodes.append({"title": work["title"], 
                        "citation_count": citation_count,
                        "doi": work["doi"],
                        "openalex_id": work["id"],
                        "year": work['publication_year'],
                        "label": 'publication', 
                        "id": target,
                        "color": 'publication',
                        "radius": pub_radius
                        })
            i += 1

            # if pub, then use scopus id
            coauthor_link = []
            temp_source = []
            
            for au in work['authorships']:
                try:
                    source = node_records[au['author']['id']]
                    
                except KeyError:
                    node_records[au['author']['id']] = i
                    source = i

                    # handle empty values
                    if len(au['institutions']) == 0:
                        country_code = ''
                        affiliation_name = ''
                    else:
                        country_code = au['institutions'][0]['country_code']
                        affiliation_name = au['institutions'][0]['display_name']

                    author = {
                                "title": au['author']['display_name'],
                                "orcid": au['author']["orcid"],
                                "openalex_id": au['author']['id'],
                                "country": country_code,
                                "affiliation": affiliation_name,
                                "label": "author",
                                "id": source,
                                "color": "author"}
                    nodes.append(author)
                    coauthor_nodes.append(author)
                    i += 1
                temp_source.append(source)
                nodes_id_in_rel.append(source)
                rels.append({"source": source, "target": target, "doi":work["doi"], "openalex_id":au['author']['id']})

            coauthor_link = coauthor_link+list(itertools.combinations(temp_source, 2))

            for l in coauthor_link:
                coauthor_rels.append({"source": l[0], "target": l[1], "doi":work["doi"], "title": work["title"]})

        nodes = get_link_count_of_author(nodes, nodes_id_in_rel)
        coauthor_nodes = get_link_count_of_author(coauthor_nodes, nodes_id_in_rel)
        coauthor_rels = get_link_count_of_rel(coauthor_rels)
        
        return Response(dumps({"nodes": nodes, "links": rels, "coauthor_nodes": coauthor_nodes, "coauthor_links": coauthor_rels
                               }),
                    mimetype="application/json")

# institution search
@app.route("/openalex-institution-network")
def openalex_inst_network():
    try:
        aff_name = request.args["aff_name"]
    except KeyError:
        return []
    else:
        aff_result = openalex.find_institution(aff_name)
        # if fetch no info
        if aff_result['meta']['count'] == 0:
            return []
        
        aff_info = aff_result['results'][0]

        display_name = aff_info['display_name']
        ror = aff_info['ror']

        works_count = aff_info['works_count']
        cite_count = aff_info['cited_by_count']
        h_index = aff_info['summary_stats']['h_index']
        
        home_page = aff_info['homepage_url']
        city = aff_info['geo']['city']
        country = aff_info['geo']['country']
        counts_by_year = aff_info['counts_by_year']
        concept_score = {}
        concept_score['concept_name'] = []
        concept_score['score'] = []
        for c in aff_info['x_concepts'][0:7]:
                concept_score['concept_name'].append(c['display_name'])
                concept_score['score'].append(c['score'])

        node_list, coauthor_link = openalex.build_institution_network(aff_name)
        for node in node_list:
            node['label'] = 'institution'
           
            coauthor_rels = []
        for l in coauthor_link:
            coauthor_rels.append({"source": l[0], "target": l[1]})

        sorted_relationships = [tuple(sorted([r['source'], r['target']])) for r in coauthor_rels]
        # count the occurrences of each tuple
        counts = Counter(sorted_relationships)
        link_result = []
        for pair, count in counts.items():
            link_result.append({'source': pair[0], 'target': pair[1], 'count': count})

        # TO BE DONE
        return Response(dumps({"nodes": node_list, "links": link_result, 
                               "aff_name": display_name, 'ror': ror, 'works_count': works_count, 'cited_by_count':cite_count,
                               'h_index':h_index, 'home_page': home_page, 'city':city, 'country':country,
                               'concept_score': concept_score, 'cite_by_year':counts_by_year
                               }),
                    mimetype="application/json")
    

if __name__ == "__main__":
    # uri = "bolt://localhost:7687"
    # username = "neo4j"
    # password = "zhiningbai"

    logging.root.setLevel(logging.INFO)
    logging.info("Starting on port %d, database is at %s", port, uri)
    app.run(port=port)

