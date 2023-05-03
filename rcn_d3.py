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

def get_link_count_of_author(author_nodes, rel_id_record):
    for author in author_nodes:
        link_num = rel_id_record.count(author["id"])
        author["link_num"] = link_num
        if link_num != 0:
            author["radius"] = 5 + math.log(link_num)
    return author_nodes


# example network: get pub-author relationships (default: 2022, "Deep learning")
@app.route("/graph")
def get_example_graph():
    def work(tx, year, search_query):
        return list(tx.run("""
            MATCH (n:Person)-[:IS_AUTHOR_OF]->(p:Publication {year: $year}) 
            WHERE   $keyword in p.keywords
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
    results = db.execute_read(work, 2022, "Deep learning")
    nodes = []
    rels = []
    node_records = []
    nodes_id_in_rel = []
    i = 0
    for record in results:
        target = i
        if math.isnan(record["cited"]):
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
                        "id": source,
                        "color": "author"}
                nodes.append(author)
                i += 1
            nodes_id_in_rel.append(source)
            rels.append({"source": source, "target": target, "doi":record["doi"], "scopus_id": record["author_scopus_id"][a]})

    nodes = get_link_count_of_author(nodes, nodes_id_in_rel)

    return Response(dumps({"nodes": nodes, "links": rels}),
                mimetype="application/json")
    # return Response(dumps({"s": x}),mimetype="application/json")

# 
@app.route('/search')
def get_search_query():
    def work(tx, year, search_query):
        return list(tx.run("""
            MATCH (n:Person)-[:IS_AUTHOR_OF]->(p:Publication) 
            WHERE   $keyword in p.keywords 
                AND p.year in $year
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
        year = request.args["year"]
        keyword = request.args["keyword"]
    except KeyError:
        return []
    else:
        db = get_db()
        year = list(map(int, year.split(",")))
        query = keyword.replace("+", " ")
        results = db.execute_read(work, year, query)
        # results = db.read_transaction(work, q)
        # return Response(
        #     dumps([serialize_movie(record["movie"]) for record in results]),
        #     mimetype="application/json"
        # )
        nodes = []
        rels = []
        node_records = []
        nodes_id_in_rel = []
        i = 0
        for record in results:
            target = i
            node_records.append(record["doi"])

            if math.isnan(record["cited"]):
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
                            "id": source,
                            "color": "author"}
                    nodes.append(author)
                    i += 1
                nodes_id_in_rel.append(source)
                rels.append({"source": source, "target": target, "doi":record["doi"], "scopus_id": record["author_scopus_id"][a]})
        nodes = get_link_count_of_author(nodes, nodes_id_in_rel)
        return Response(dumps({"nodes": nodes, "links": rels}),
                    mimetype="application/json")
       


@app.route('/orcid_search')
def get_orcid_search():
    def get_coauthor_byID(tx, scopus_id, orcid):
        return list(tx.run("""
            MATCH (n:Person)-[:IS_AUTHOR_OF]->(p)
                    <-[:IS_AUTHOR_OF]-(m:Person)
            WHERE labels(p) IN [['Publication'], ['Project'], ['Software']] AND
                    (n.orcid = $orcid OR n.scopus_id = $scopus_id)
            RETURN  
                    apoc.coll.toSet(collect(n.scopus_id)+collect(m.scopus_id)) AS author_scopus_id,
                    apoc.coll.toSet(collect(n.orcid)+collect(m.orcid)) AS author_orcid,
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
    
    # def first_coauthor_byORCID(tx, orcid):
    #     return list(tx.run("""
    #         MATCH (n:Person {orcid: $orcid})-[:IS_AUTHOR_OF]->(item)<-[:IS_AUTHOR_OF]-(m:Person)
    #         RETURN  apoc.coll.toSet(collect(n.orcid)+collect(m.orcid)) AS orcid,
    #                 apoc.coll.toSet(collect(n.scopus_id)+collect(m.scopus_id)) AS scopus_id,
    #                 item.title AS title,
    #                 item.cited AS cited,
    #                 item.year AS year,
    #                 item.subject AS subject,
    #                 item.doi AS doi,
    #             CASE 
    #                 WHEN labels(item) = ['Project'] THEN  'project'
    #                 WHEN labels(item) = ['Software'] THEN 'software'
    #                 WHEN labels(item) = ['Publication'] THEN 'publication'
    #                 ELSE '' 
    #             END AS label
    #         """,
    #         orcid = orcid
    #     ))
    
    def get_author_byName(tx, name):
        return list(tx.run("""
            MATCH (n:Person {name: $name})-[:IS_AUTHOR_OF]->(p:Publication)
                    <-[:IS_AUTHOR_OF]-(m:Person)
            RETURN  
                    apoc.coll.toSet(collect(n.scopus_id)+collect(m.scopus_id)) AS author_scopus_id,
                    p.title AS title,
                    p.cited AS cited,
                    p.doi AS doi,
                    p.subject AS subject,
                    p.year AS year
            """,
            name = name
        ))
    
    def get_coauthor_info_scopus(tx, scopus_id):
        return list(tx.run("""
            MATCH (n:Person {scopus_id: $scopus_id})
            RETURN  
                    n.name AS name,
                    n.country AS country,
                    n.affiliation AS aff
            """,
            scopus_id = scopus_id
        ))
    def get_coauthor_info_rsd(tx, orcid):
         return list(tx.run("""
            MATCH (n:Person {orcid: $orcid})
            RETURN  
                    n.name AS name,
                    n.affiliation AS aff
            """,
            orcid = orcid
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
        firstname = request.args["firstname"]
        surname = request.args["surname"]
    except KeyError:
        return []
    else:
        db = get_db()
        scopus_id = neo4j_rsd.get_scopus_info_from_orcid(orcid)[0]
        results = db.execute_read(get_coauthor_byID, scopus_id, orcid)
        
        # second_results = db.read_transaction(second_coauthor, scopus_id)
        # results = db.read_transaction(work, q)
        # return Response(
        #     dumps([serialize_movie(record["movie"]) for record in results]),
        #     mimetype="application/json"
        # )
        nodes = []
        rels = []
        node_records = []
        nodes_id_in_rel = []
        i = 0
        for record in results:
            target = i
            node_records.append(record['doi'])
            # Citation Count
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
            if record["label"] == "publication":
                for id in record["author_scopus_id"]:
                    # Get coauthor info from DB
                    co_author_results = db.execute_read(get_coauthor_info_scopus, id)
                    name = co_author_results[0]["name"]
                    country = co_author_results[0]["country"]
                    aff = co_author_results[0]["aff"]

                    if id == scopus_id:
                        author_color = "author_highlight"
                    else:
                        author_color = "first_coauthor"

                    try:
                        if (id == scopus_id) and (orcid in node_records):
                            source = node_records.index(orcid) 
                        else:
                            source = node_records.index(id)
                    except ValueError:
                        node_records.append(id)
                        source = i
                        author = {"title": name,
                                "scopus_id": id,
                                "country": country,
                                "affiliation": aff,
                                "label": "author",
                                "id": source,
                                "color": author_color}
                        nodes.append(author)
                        i += 1
                    nodes_id_in_rel.append(source)
                    rels.append({"source": source, "target": target, "doi":record["doi"], "scopus_id": id})
            else:
                for id in record["author_orcid"]:
                    # Get coauthor info from DB
                    co_author_results = db.execute_read(get_coauthor_info_rsd, id)
                    name = co_author_results[0]["name"]
                    aff = co_author_results[0]["aff"]

                    if id == orcid:
                        author_color = "author_highlight"
                    else:
                        author_color = "first_coauthor"

                    try:
                        if (id == orcid) and (scopus_id in node_records):
                            source = node_records.index(scopus_id) 
                        else:
                            source = node_records.index(id)
                    except ValueError:
                        node_records.append(id)
                        source = i
                        author = {"title": name,
                                "orcid": id,
                                "affiliation": aff,
                                "label": "author",
                                "id": source,
                                "color": author_color}
                        nodes.append(author)
                        i += 1
                    nodes_id_in_rel.append(source)
                    rels.append({"source": source, "target": target, "doi":record["doi"], "orcid": id})
        nodes = get_link_count_of_author(nodes, nodes_id_in_rel)
        return Response(dumps({"nodes": nodes, "links": rels}),
                    mimetype="application/json")
      



@app.route('/pub_search')
def get_pub_search():
    def doi_search(tx, doi):
        return list(tx.run("""
            MATCH (n:Person)-[:IS_AUTHOR_OF]->(p:Publication {doi: $doi})
            RETURN  
                    collect(n.scopus_id) AS author_scopus_id,
                    collect(n.name) AS name,
                    collect(n.country) AS country,
                    collect(n.affiliation) AS affiliation,
                    p.title AS title,
                    p.cited AS cited,
                    p.subject AS subject,
                    p.year AS year
            """,
            doi = doi
        ))
    
    try:
        doi = request.args["doi"]
    except KeyError:
        return []
    else:
        db = get_db()
        # doi = doi.replace("%2F", "/")
        results = db.execute_read(doi_search, doi)
        nodes = []
        rels = []
        i = 0

        record = results[0]
        target = i
        if math.isnan(record["cited"]):
            citation_count = 0
            pub_radius = 6
        else:
            citation_count = record["cited"]
            pub_radius = 6 + math.log(citation_count)

        nodes.append({"title": record["title"], 
                        "citation_count": citation_count,
                        "doi": doi,
                        "subject": record["subject"],
                        "year": record["year"],
                        "label": "publication", 
                        "id": target,
                        "color": "publication",
                        "radius": pub_radius})
        i += 1
        for a in range(len(record["author_scopus_id"])):
            source = i
            author = {"title": record["name"][a],
                            "scopus_id": record["author_scopus_id"][a],
                            "country": record["country"][a],
                            "affiliation": record["affiliation"][a],
                            "label": "author",
                            "id": source,
                            "color": "author",
                            "radius": 5
                            }
            nodes.append(author)
            i += 1
            rels.append({"source": source, "target": target, "doi":doi, "scopus_id": record["author_scopus_id"][a]})
    return Response(dumps({"nodes": nodes, "links": rels}),
                mimetype="application/json")


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
            results = db.execute_read(pub_node, unique_id)
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
                    rels.append({"source": max_id, "target": node_id, "doi": unique_id, "scopus_id": record['scopus_id']})

        if node_label == "author":
            results = db.execute_read(person_node, unique_id)
            for record in results:
                if record['doi'] not in link_list:
                    if math.isnan(record["cited"]):
                        citation_count = 0
                        pub_radius = 6
                    else:
                        citation_count = record["cited"]
                        pub_radius = 6 + math.log(citation_count)
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
    
        return Response(dumps({"nodes": nodes, "links": rels}),
                    mimetype="application/json")
    


if __name__ == "__main__":
    # uri = "bolt://localhost:7687"
    # username = "neo4j"
    # password = "zhiningbai"

    logging.root.setLevel(logging.INFO)
    logging.info("Starting on port %d, database is at %s", port, uri)
    app.run(port=port)

