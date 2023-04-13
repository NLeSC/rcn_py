from json import dumps
import logging
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
            RETURN collect(n.name) AS author,
                   p.title AS title
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
    records = []
    i = 0
    x = 0
    for record in results:
        target = i
        nodes.append({"title": record["title"], "label": "publication", "id": target, "group":target})
        i += 1
        for name in record["author"]:
            if records == []:
                records.append({"title": name, "label": "author"})
                source = i
                author = {"title": name, "label": "author", "id": source, "group":target}
                nodes.append(author)
                i += 1
            else:
                try:
                    source = records.index({"title": name, "label": "author"})
                    x += 1
                except ValueError:
                    records.append({"title": name, "label": "author"})
                    source = i
                    author = {"title": name, "label": "author", "id": source, "group":target}
                    nodes.append(author)
                    i += 1
            rels.append({"source": source, "target": target})
    return Response(dumps({"nodes": nodes, "links": rels}),
                mimetype="application/json")
    # return Response(dumps({"s": x}),mimetype="application/json")

# 
@app.route('/search')
def get_search_query():
    def work(tx, year, keyword):
        return list(tx.run("""
            MATCH (n:Person)-[:IS_AUTHOR_OF]->(p:Publication {year: $year}) 
            WHERE $keyword in p.keywords
            RETURN collect(n.name) AS author,
                   p.title AS title
            LIMIT $limit
            """,
            year = year,
            keyword = keyword,
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
        records = []
        i = 0
        for record in results:
            target = i
            nodes.append({"title": record["title"], "label": "publication", "id": target})
            i += 1
            for name in record["author"]:
                author = {"title": name, "label": "author"}
                try:
                    source = records.index(author)
                except ValueError:
                    records.append(author)
                    source = i
                    author["id"] = source
                    nodes.append(author)
                    i += 1
                rels.append({"source": source, "target": target})
        return Response(dumps({"nodes": nodes, "links": rels}),
                    mimetype="application/json")
        
        # return Response(dumps({"year": year, "keyword": keyword, "title": results}),
        #                  mimetype="application/json")


@app.route('/orcid_search')
def get_orcid_search():
    def first_coauthor(tx, scopus_id):
        return list(tx.run("""
            MATCH (n:Person {scopus_id: $scopus_id})-[:IS_AUTHOR_OF]->(p:Publication)
                    <-[:IS_AUTHOR_OF]-(m:Person)
            RETURN  apoc.coll.toSet(collect(n.scopus_id)+collect(m.scopus_id)) AS first_coauthor_id,
                    apoc.coll.toSet(collect(n.name)+collect(m.name)) AS first_coauthor_name,
                    p.title AS first_pub
            """,
            scopus_id = scopus_id
        ))
    
    def second_coauthor(tx, scopus_id):
        return list(tx.run("""
            MATCH (n:Person {scopus_id: $scopus_id})-[:IS_AUTHOR_OF]->(p:Publication)
                    <-[:IS_AUTHOR_OF]-(m:Person)-[:IS_AUTHOR_OF]->(q:Publication)
                    <-[:IS_AUTHOR_OF]-(l:Person)
            RETURN  apoc.coll.toSet(collect(l.scopus_id)) AS second_coauthor_id,

                    apoc.coll.toSet(collect(l.scopus_id)) AS second_coauthor_id,
                    apoc.coll.toSet(collect(m.name)+collect(l.name)) AS second_coauthor_name,
                    q.title AS second_pub
            LIMIT $limit
            """,
            scopus_id = scopus_id,
            limit = 100
        ))
    
    try:
        orcid = request.args["orcid"]
    except KeyError:
        return []
    else:
        db = get_db()
        scopus_id = neo4j_rsd.get_scopus_info_from_orcid(orcid)[0]
        first_results = db.read_transaction(first_coauthor, scopus_id)
        # second_results = db.read_transaction(second_coauthor, scopus_id)
        # results = db.read_transaction(work, q)
        # return Response(
        #     dumps([serialize_movie(record["movie"]) for record in results]),
        #     mimetype="application/json"
        # )
        nodes = []
        rels = []
        i = 0

        for record in first_results:
            nodes.append({"title": record["first_pub"], "label": "first_pub"})
            target = i
            i += 1
            for index in range(len(record["first_coauthor_name"])):

                if record["first_coauthor_id"][index] == scopus_id:
                    author = {"title": record["first_coauthor_name"][index], "label": "author_highlight"}
                else:
                    author = {"title": record["first_coauthor_name"][index], "label": "first_coauthor"}

                try:
                    source = nodes.index(author)
                except ValueError:
                    nodes.append(author)
                    source = i
                    i += 1
                rels.append({"source": source, "target": target})


        # for record in second_results:
        #     nodes.append({"title": record["second_pub"], "label": "second_pub"})
        #     target = i
        #     i += 1
        #     for name in record["second_coauthor_name"]:
        #         author = {"title": name, "label": "second_coauthor"}
        #         try:
        #             source = nodes.index(author)
        #         except ValueError:
        #             nodes.append(author)
        #             source = i
        #             i += 1
        #         rels.append({"source": source, "target": target})
        
        return Response(dumps({"nodes": nodes, "links": rels}),
                        mimetype="application/json")
        
        # return Response(dumps({"year": year, "keyword": keyword, "title": results}),
        #                  mimetype="application/json")


if __name__ == "__main__":
    # uri = "bolt://localhost:7687"
    # username = "neo4j"
    # password = "zhiningbai"

    logging.root.setLevel(logging.INFO)
    logging.info("Starting on port %d, database is at %s", port, uri)
    app.run(port=port)

