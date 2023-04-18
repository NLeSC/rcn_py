from json import dumps
import logging
import math
import os
import sys
from flask import (
    Flask,
    g,
    request,
    Response,
)
from neo4j import (
    GraphDatabase,
)
from rcn_py import neo4j_rsd

# uri = "bolt://localhost:7687"
# username = "neo4j"
# password = "zhiningbai"

# app = Flask(__name__, static_url_path="/static/")
# port = os.getenv("PORT", 8081)
# driver = GraphDatabase.driver(uri, auth=(username, password))
uri = sys.argv[1]
username = sys.argv[2]
password = sys.argv[3]

app = Flask(__name__, static_url_path="/static/")
port = os.getenv("PORT", 8081)
driver = GraphDatabase.driver(uri, auth=(username, password))

# driver.session(database="neo4j")
def get_db():
    if not hasattr(g, "neo4j_db"):
        # if neo4j_version >= "4":
            g.neo4j_db = driver.session(database="neo4j")
        # else:
        #     g.neo4j_db = driver.session()
    return g.neo4j_db

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, "neo4j_db"):
        g.neo4j_db.close()

@app.route("/")
def get_index():
    return app.send_static_file("index_v7.html")


def serialize_person(person):
    return {
        "scopus_id": person["scopus_id"],
        "name": person["name"],
        "affiliation": person["affiliation"],
        "country": person["country"],
        "subject": person["subject"],
        "keywords": person["keywords"],
        "year": person["year"]
    }

def serialize_publication(pub):
    return {
        "doi": pub["doi"],
        "title": pub["title"],
        "subject": pub["subject"],
        "keywords": pub["keywords"],
        "year": pub["year"],
        "cited": pub["cited"]
    }


# example network: get pub-author relationships (default: 2022, "Deep learning")
@app.route("/graph")
def get_example_graph():
    def work(tx, year, search_query):
        return list(tx.run("""
            MATCH (n:Person)-[:IS_AUTHOR_OF]->(p:Publication {year: $year}) 
            WHERE  $keyword in p.keywords
            RETURN  collect(n.scopus_id) AS author_scopus_id,
                    collect(n.name) AS name,
                    collect(n.country) AS country,
                    collect(n.affiliation) AS affiliation,
                    p.title AS title,
                    p.cited AS cited,
                    p.doi AS doi,
                    p.subject AS subject,
                    p.year AS year
            LIMIT $limit
            """,
            year = year,
            keyword = search_query,
            limit = 100
        ))
    
    db = get_db()
    results = db.read_transaction(work, 2022, "Deep learning")
    nodes = []
    rels = []
    node_records = []
    i = 0
    for record in results:
        target = i
        if math.isnan(record["cited"]):
            citation_count = 0
        else:
            citation_count = record["cited"]
        nodes.append({"title": record["title"], 
                      "citation_count": citation_count,
                      "doi": record["doi"],
                      "subject": record["subject"],
                      "year": record["year"],
                      "label": "publication", 
                      "id": target})
        i += 1
        for a in range(len(record["author_scopus_id"])):
            
            try:
                source = node_records.index(record["name"][a])
            except ValueError:
                node_records.append(record["name"][a])
                source = i
                author = {"title": record["name"][a],
                        "scopus_id": record["author_scopus_id"][a],
                        "country": record["country"][a],
                        "affiliation": record["affiliation"][a],
                        "label": "author",
                        "id": source}
                nodes.append(author)
                i += 1
            rels.append({"source": source, "target": target, "doi":record["doi"], "scopus_id": record["author_scopus_id"][a]})
    return Response(dumps({"nodes": nodes, "links": rels}),
                mimetype="application/json")
    # return Response(dumps({"s": x}),mimetype="application/json")

# 
@app.route('/search')
def get_search_query():
    def work(tx, year, search_query):
        return list(tx.run("""
            MATCH (n:Person)-[:IS_AUTHOR_OF]->(p:Publication {year: $year}) 
            WHERE  $keyword in p.keywords
            RETURN  collect(n.scopus_id) AS author_scopus_id,
                    collect(n.name) AS name,
                    collect(n.country) AS country,
                    collect(n.affiliation) AS affiliation,
                    p.title AS title,
                    p.cited AS cited,
                    p.doi AS doi,
                    p.subject AS subject,
                    p.year AS year
            LIMIT $limit
            """,
            year = year,
            keyword = search_query,
            limit = 100
        ))

    try:
        year = int(request.args["year"])
        keyword = request.args["keyword"]
    except KeyError:
        return []
    else:
        db = get_db()
        query = keyword.replace("+", " ")
        results = db.read_transaction(work, year, query)
        # results = db.read_transaction(work, q)
        # return Response(
        #     dumps([serialize_movie(record["movie"]) for record in results]),
        #     mimetype="application/json"
        # )
        nodes = []
        rels = []
        node_records = []
        i = 0
        for record in results:
            target = i
            node_records.append(record["doi"])

            if math.isnan(record["cited"]):
                citation_count = 0
            else:
                citation_count = record["cited"]
            nodes.append({"title": record["title"], 
                        "citation_count": citation_count,
                        "doi": record["doi"],
                        "subject": record["subject"],
                        "year": record["year"],
                        "label": "publication", 
                        "id": target})
            i += 1
            for a in range(len(record["author_scopus_id"])):
                
                try:
                    source = node_records.index(record["name"][a])
                except ValueError:
                    node_records.append(record["name"][a])
                    source = i
                    author = {"title": record["name"][a],
                            "scopus_id": record["author_scopus_id"][a],
                            "country": record["country"][a],
                            "affiliation": record["affiliation"][a],
                            "label": "author",
                            "id": source}
                    nodes.append(author)
                    i += 1
                rels.append({"source": source, "target": target, "doi":record["doi"], "scopus_id": record["author_scopus_id"][a]})
        return Response(dumps({"nodes": nodes, "links": rels}),
                    mimetype="application/json")


@app.route('/orcid_search')
def get_orcid_search():
    def first_coauthor(tx, scopus_id):
        return list(tx.run("""
            MATCH (n:Person {scopus_id: $scopus_id})-[:IS_AUTHOR_OF]->(p:Publication)
                    <-[:IS_AUTHOR_OF]-(m:Person)
            RETURN  
                    apoc.coll.toSet(collect(n.scopus_id)+collect(m.scopus_id)) AS author_scopus_id,
                    p.title AS title,
                    p.cited AS cited,
                    p.doi AS doi,
                    p.subject AS subject,
                    p.year AS year
            """,
            scopus_id = scopus_id
        ))
    def get_coauthor_info(tx, scopus_id):
        return list(tx.run("""
            MATCH (n:Person {scopus_id: $scopus_id})
            RETURN  
                    n.name AS name,
                    n.country AS country,
                    n.affiliation AS aff
            """,
            scopus_id = scopus_id
        ))
    #
    # def second_coauthor(tx, scopus_id):
    #     return list(tx.run("""
    #         MATCH (n:Person {scopus_id: $scopus_id})-[:IS_AUTHOR_OF]->(p:Publication)
    #                 <-[:IS_AUTHOR_OF]-(m:Person)-[:IS_AUTHOR_OF]->(q:Publication)
    #                 <-[:IS_AUTHOR_OF]-(l:Person)
    #         RETURN  apoc.coll.toSet(collect(l.scopus_id)) AS second_coauthor_id,

    #                 apoc.coll.toSet(collect(l.scopus_id)) AS second_coauthor_id,
    #                 apoc.coll.toSet(collect(m.name)+collect(l.name)) AS second_coauthor_name,
    #                 q.title AS second_pub
    #         LIMIT $limit
    #         """,
    #         scopus_id = scopus_id,
    #         limit = 100
    #     ))
    
    try:
        orcid = request.args["orcid"]
    except KeyError:
        return []
    else:
        db = get_db()
        scopus_id = neo4j_rsd.get_scopus_info_from_orcid(orcid)[0]
        results = db.read_transaction(first_coauthor, scopus_id)
        # second_results = db.read_transaction(second_coauthor, scopus_id)
        # results = db.read_transaction(work, q)
        # return Response(
        #     dumps([serialize_movie(record["movie"]) for record in results]),
        #     mimetype="application/json"
        # )
        nodes = []
        rels = []
        node_records = []
        i = 0
        for record in results:
            target = i
            node_records.append(record['doi'])
            if math.isnan(record["cited"]):
                citation_count = 0
            else:
                citation_count = record["cited"]
            nodes.append({"title": record["title"], 
                        "citation_count": citation_count,
                        "doi": record["doi"],
                        "subject": record["subject"],
                        "year": record["year"],
                        "label": "publication", 
                        "id": target})
            i += 1
            for id in record["author_scopus_id"]:
                # Get coauthor info from DB
                co_author_results = db.read_transaction(get_coauthor_info, id)
                name = co_author_results[0]["name"]
                country = co_author_results[0]["country"]
                aff = co_author_results[0]["aff"]

                if id == scopus_id:
                    author_label = "author_highlight"
                else:
                    author_label = "first_coauthor"

                try:
                    source = node_records.index(id)
                except ValueError:
                    node_records.append(id)
                    source = i
                    author = {"title": name,
                            "scopus_id": id,
                            "country": country,
                            "affiliation": aff,
                            "label": author_label,
                            "id": source}
                    nodes.append(author)
                    i += 1
                        
                rels.append({"source": source, "target": target, "doi":record["doi"], "scopus_id": id})
        return Response(dumps({"nodes": nodes, "links": rels}),
                    mimetype="application/json")
      

@app.route('/show_link')
def show_link():

    def person_node(tx, scopus_id):
        return list(tx.run("""
            MATCH (n:Person {scopus_id: $scopus_id})-[r]->(p) 
            RETURN  p.title AS title,
                    p.cited AS cited,
                    p.doi AS doi,
                    p.subject AS subject,
                    p.year AS year
            LIMIT $limit
            """,
            scopus_id = scopus_id,
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
    except KeyError:
        return []
    else:
        nodes = []
        rels = []
        link_list = linkList.split(',')

        db = get_db()
        if node_label == "publication":
            results = db.read_transaction(pub_node, unique_id)
            for record in results:
                if record['scopus_id'] not in link_list:
                    max_id += 1
                    author = {"title": record['name'],
                            "scopus_id": record['scopus_id'],
                            "country": record['country'],
                            "affiliation": record['affiliation'],
                            "label": "author",
                            "id": max_id}
                    nodes.append(author)
                    rels.append({"source": max_id, "target": node_id, "doi": unique_id, "scopus_id": record['scopus_id']})

        else:
            results = db.read_transaction(person_node, unique_id)
            for record in results:
                if record['doi'] not in link_list:
                    if math.isnan(record["cited"]):
                        citation_count = 0
                    else:
                        citation_count = record["cited"]
                    max_id += 1
                    nodes.append({"title": record["title"], 
                        "citation_count": citation_count,
                        "doi": record["doi"],
                        "subject": record["subject"],
                        "year": record["year"],
                        "label": "publication", 
                        "id": max_id})
                    rels.append({"source": node_id, "target": max_id, "doi": record["doi"], "scopus_id": unique_id})
    
        return Response(dumps({"nodes": nodes, "links": rels}),
                    mimetype="application/json")

if __name__ == "__main__":
    # uri = "bolt://localhost:7687"
    # username = "neo4j"
    # password = "zhiningbai"

    logging.root.setLevel(logging.INFO)
    logging.info("Starting on port %d, database is at %s", port, uri)
    app.run(port=port)

