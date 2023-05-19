from json import dumps
import logging
import math
import os
import sys
import requests
import itertools
from collections import Counter
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
from rcn_py import orcid as orcid_py
from rcn_py import openalex

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
def get_db(database):
    if not hasattr(g, "neo4j_db"):
        # if neo4j_version >= "4":
            g.neo4j_db = driver.session(database=database)
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

def get_link_count_of_rel(relationships):
    # create a list of tuples with sorted source and target values
    sorted_relationships = [tuple(sorted([r['source'], r['target']])) for r in relationships]

    # count the occurrences of each tuple
    counts = Counter(sorted_relationships)

    result = []
    for pair, count in counts.items():
        titles = [d['title'] for d in relationships if ((d['source'], d['target']) == pair or (d['target'], d['source']) == pair)]
        dois = [d['doi'] for d in relationships if ((d['source'], d['target']) == pair or (d['target'], d['source']) == pair)]
        result.append({'source': pair[0], 'target': pair[1], 'count': count, 'title': titles, 'doi':dois})

    return result



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
    
    db = get_db("neo4j")
    results = db.execute_read(work, 2022, "Deep learning")
    nodes = []
    rels = []
    node_records = []
    nodes_id_in_rel = []

    coauthor_nodes = []
    coauthor_rels = [] 

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

        # link = link+list(itertools.combinations(record["author_scopus_id"], 2))
        coauthor_link = []
        temp_source = []
        for a in range(len(record["author_scopus_id"])):
            try:
                source = node_records.index(record["author_scopus_id"][a])

            except ValueError:
                node_records.append(record["author_scopus_id"][a])
                source = i
                author = {"title": record["name"][a],
                        "scopus_id": record["author_scopus_id"][a],
                        "country": record["country"][a],
                        "affiliation": record["affiliation"][a],
                        "label": "author",
                        "id": source,
                        "color": "author"}
                nodes.append(author)
                coauthor_nodes.append(author)
                i += 1
            temp_source.append(source)
            nodes_id_in_rel.append(source)
            rels.append({"source": source, "target": target, "doi":record["doi"], "scopus_id": record["author_scopus_id"][a]})

        coauthor_link = coauthor_link+list(itertools.combinations(temp_source, 2))

        for l in coauthor_link:
            coauthor_rels.append({"source": l[0], "target": l[1], "doi":record["doi"], "title": record["title"]})

    nodes = get_link_count_of_author(nodes, nodes_id_in_rel)
    coauthor_nodes = get_link_count_of_author(coauthor_nodes, nodes_id_in_rel)
    coauthor_rels = get_link_count_of_rel(coauthor_rels)

    return Response(dumps({"nodes": nodes, "links": rels, "coauthor_nodes": coauthor_nodes, "coauthor_links": coauthor_rels}),
                mimetype="application/json")
    # return Response(dumps({"coauthor_nodes": coauthor_nodes, "coauthor_links": coauthor_rels}),
    #             mimetype="application/json")
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
        db = get_db("neo4j")
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
        coauthor_nodes = []
        coauthor_rels = [] 

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
            coauthor_link = []
            temp_source = []

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
                    coauthor_nodes.append(author)
                    i += 1
                temp_source.append(source)
                nodes_id_in_rel.append(source)
                rels.append({"source": source, "target": target, "doi":record["doi"], "scopus_id": record["author_scopus_id"][a]})
        
            coauthor_link = coauthor_link+list(itertools.combinations(temp_source, 2))

            for l in coauthor_link:
                coauthor_rels.append({"source": l[0], "target": l[1], "doi":record["doi"], "title": record["title"]})

        nodes = get_link_count_of_author(nodes, nodes_id_in_rel)
        coauthor_nodes = get_link_count_of_author(coauthor_nodes, nodes_id_in_rel)
        coauthor_rels = get_link_count_of_rel(coauthor_rels)
        
        return Response(dumps({"nodes": nodes, "links": rels, "coauthor_nodes": coauthor_nodes, "coauthor_links": coauthor_rels}),
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
    
    def get_coauthor_byName(tx, namelist):
        return list(tx.run("""
            MATCH (n:Person)-[:IS_AUTHOR_OF]->(p)
                    <-[:IS_AUTHOR_OF]-(m:Person)
            WHERE labels(p) IN [['Publication'], ['Project'], ['Software']] AND
                    (n.name in $namelist)
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
            namelist = namelist
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
        escience = request.args["escience"]
    except KeyError:
        return []
    else:
        if escience:
            db = get_db("rsd")
            # OpenAlex can be used to add more results (todo)
        else:
            db = get_db("neo4j")
        

        # scopus_id = neo4j_rsd.get_scopus_info_from_orcid(orcid)[0]
        # db = get_db("rsd")

        if (not orcid) or (firstname and surname):
            orcid = orcid_py.name_to_orcid_id(firstname+' '+surname)
        if orcid:
            # rsd data
            scopus_id = neo4j_rsd.get_scopus_info_from_orcid(orcid)[0]
            results = db.execute_read(get_coauthor_byID, scopus_id, orcid)

            # openAlex
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



        #     works_results = openalex.search_works_by_orcid(orcid)
            
        #     nodes = []
        #     rels = []
        #     node_records = []
        #     nodes_id_in_rel = []
        #     i = 0
        #     coauthor_nodes = []
        #     coauthor_rels = [] 

        #     for work in works_results['results']:
        #         target = i
        #         node_records.append(work['doi'])

        #         if work["cited_by_count"] > 0:
        #             pub_radius = 6 + math.log(work["cited_by_count"])
        #         else:
        #             pub_radius = 6
        #         nodes.append({"title": work["title"], 
        #                 "citation_count": work["cited_by_count"],
        #                 "doi": work["doi"],
        #                 "year": work["publication_year"],
        #                 "label": work["type"], 
        #                 "id": target,
        #                 "color": "publication",
        #                 "radius": pub_radius
        #                 })
        #         i += 1
        #         temp_source = []
        #         coauthor_link = []
                
        #         for au in work['authorships']:
        #             if not au["author"]["orcid"]:
        #                 new_orcid = orcid_py.name_to_orcid_id(au["author"]["display_name"])
        #             else:
        #                 new_orcid = au["author"]["orcid"]
                    

        #             if orcid == new_orcid:
        #                 author_color = "author_highlight"
        #             else:
        #                 author_color = "first_coauthor"

        #             try:
        #                 source = node_records.index(new_orcid)
        #             except ValueError:
        #                 new_author_name = au["author"]["display_name"]
        #                 if au['institutions']:
        #                     new_country = au['institutions'][0]['country_code']
        #                     new_aff_name = au['institutions'][0]['display_name']
        #                 else:
        #                     new_country = ''
        #                     new_aff_name = ''

        #                 node_records.append(new_orcid)
        #                 source = i

        #                 author = {"title": new_author_name,
        #                         "scopus_id": new_orcid,
        #                         "country": new_country,
        #                         "affiliation": new_aff_name,
        #                         "label": "author",
        #                         "id": source,
        #                         "color": author_color}
                        
        #                 nodes.append(author)
        #                 coauthor_nodes.append(author)
        #                 i += 1
        #             temp_source.append(source)
        #             nodes_id_in_rel.append(source)
        #             rels.append({"source": source, "target": target, "doi":work["doi"], "scopus_id": id})

        #         coauthor_link = coauthor_link+list(itertools.combinations(temp_source, 2))

        #     for l in coauthor_link:
        #         coauthor_rels.append({"source": l[0], "target": l[1], "doi":work["doi"], "title": work["title"]})

        # nodes = get_link_count_of_author(nodes, nodes_id_in_rel)
        # coauthor_nodes = get_link_count_of_author(coauthor_nodes, nodes_id_in_rel)
        # coauthor_rels = get_link_count_of_rel(coauthor_rels)
            
        # return Response(dumps({"nodes": nodes, "links": rels, "coauthor_nodes": coauthor_nodes, "coauthor_links": coauthor_rels,
        #                        "search_author_name": search_author_name, "works_count": works_count,"cited_by_count": cited_by_count,
        #                        "h_index": h_index, "ror": ror, "search_aff_name": search_aff_name, "search_country":search_country,
        #                        "cite_by_year": cite_by_year, "concept_score": concept_score}),
        #             mimetype="application/json")

        elif firstname and surname:
            namelist = []
            namelist.append(firstname + ' ' + surname)
            namelist.append(surname + ' ' + firstname[0]+ ".")
            namelist.append(firstname[0]+ ". "+surname)
            results = db.execute_read(get_coauthor_byName, namelist)       
        

       
        nodes = []
        rels = []
        node_records = []
        nodes_id_in_rel = []
        i = 0
        coauthor_nodes = []
        coauthor_rels = [] 

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
            temp_source = []
            coauthor_link = []
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
                        coauthor_nodes.append(author)
                        i += 1
                    temp_source.append(source)
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
                        coauthor_nodes.append(author)
                        i += 1
                    temp_source.append(source)
                    nodes_id_in_rel.append(source)
                    rels.append({"source": source, "target": target, "doi":record["doi"], "orcid": id})
            coauthor_link = coauthor_link+list(itertools.combinations(temp_source, 2))

            for l in coauthor_link:
                coauthor_rels.append({"source": l[0], "target": l[1], "doi":record["doi"], "title": record["title"]})

        nodes = get_link_count_of_author(nodes, nodes_id_in_rel)
        coauthor_nodes = get_link_count_of_author(coauthor_nodes, nodes_id_in_rel)
        coauthor_rels = get_link_count_of_rel(coauthor_rels)
            
        return Response(dumps({"nodes": nodes, "links": rels, "coauthor_nodes": coauthor_nodes, "coauthor_links": coauthor_rels,
                               "search_author_name": search_author_name, "works_count": works_count,"cited_by_count": cited_by_count,
                               "h_index": h_index, "ror": ror, "search_aff_name": search_aff_name, "search_country":search_country,
                               "cite_by_year": cite_by_year, "concept_score": concept_score}),
                    mimetype="application/json")



# ################################ Publication DOI search ################################
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
        if "https://doi.org/" in doi:
            doi = doi.replace("https://doi.org/",'')
        openalex_pub_result = openalex.get_pub_info_by_doi(doi)
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
        

        db = get_db("neo4j")
        # doi = doi.replace("%2F", "/")
        results = db.execute_read(doi_search, doi)
        

        nodes = []
        rels = []
        i = 0
        coauthor_nodes = []
        coauthor_rels = [] 

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
        temp_source = []
        coauthor_link = []
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
            coauthor_nodes.append(author)
            temp_source.append(source)
            i += 1
            rels.append({"source": source, "target": target, "doi":doi, "scopus_id": record["author_scopus_id"][a]})
        coauthor_link = coauthor_link+list(itertools.combinations(temp_source, 2))
        for l in coauthor_link:
            coauthor_rels.append({"source": l[0], "target": l[1], "count": 1,"doi":doi, "title": record["title"]})

    return Response(dumps({"nodes": nodes, "links": rels, "coauthor_nodes": coauthor_nodes, "coauthor_links": coauthor_rels,
                           "title": title, 'doi': doi, 'author_string': author_string, 'author_list':author_list,
                           'orcid_list':orcid_list, 'date': date, 'source_issn':source_issn,
                           'cited_by_count':cited_by_count, 'concept_score': concept_score, 'cite_by_year':cite_by_year}),
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

        db = get_db("neo4j")
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
                coauthor_rels.append({"source": l[0], "target": l[1], "count": 1,"doi":unique_id})
            coauthor_nodes = nodes
            


        if node_label == "author":
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
            coauthor_link = coauthor_link+list(itertools.combinations(coauthorID, 2))
            for l in coauthor_link:
                coauthor_rels.append({"source": l[0], "target": l[1], "count": 1, "id": unique_id})
            coauthor_nodes = nodes

        return Response(dumps({"nodes": nodes, "links": rels, "coauthor_nodes": coauthor_nodes, "coauthor_links": coauthor_rels}),
                    mimetype="application/json")
    

# #################################### eScience #########################################
# This is an initial network for escience, that only contains the nodes and links from eScience

@app.route("/escience")
def show_esc_graph():
    def work(tx):
        return list(tx.run("""
            MATCH (n:Person)-[:IS_AUTHOR_OF]->(p)
            WHERE   labels(p) IN [['Publication'], ['Project'], ['Software']] AND
                    n.affiliation = "Netherlands eScience Center"
            RETURN  collect(n.scopus_id) AS au_scopus_id,
                    collect(n.orcid) AS orcid,
                    p.title AS title,
                    p.cited AS cited,
                    p.doi AS doi,
                    p.subject AS subject,
                    p.year AS year,
                    p.project_id AS project_id,
                    p.software_id AS software_id,
                    CASE 
                        WHEN labels(p) = ['Project'] THEN  'project'
                        WHEN labels(p) = ['Software'] THEN 'software'
                        WHEN labels(p) = ['Publication'] THEN 'publication'
                        ELSE '' 
                    END AS label
            LIMIT $limit
            """,
            limit = 500
        ))
        
        # MATCH "name" SLOW!
    def get_esc_info(tx, name):
        return list(tx.run("""
            MATCH (n:Person {name:$name})
            WHERE  n.affiliation = "Netherlands eScience Center"
            RETURN  n.scopus_id AS scopus_id,
                    n.affiliation AS affiliation,
                    n.country AS country,
                    n.orcid AS orcid
            """,
            name = name
        ))
    
    def get_esc_info_scoid(tx, scopus_id):
        return list(tx.run("""
            MATCH (n:Person {scopus_id:$scopus_id})
            WHERE  n.affiliation = "Netherlands eScience Center"
            RETURN  n.scopus_id AS scopus_id,
                    n.name AS name,
                    n.affiliation AS affiliation,
                    n.country AS country,
                    n.orcid AS orcid
            """,
            scopus_id = scopus_id
        ))
    
    def get_esc_info_orcid(tx, orcid):
        return list(tx.run("""
            MATCH (n:Person {orcid:$orcid})
            WHERE  n.affiliation = "Netherlands eScience Center"
            RETURN  n.scopus_id AS scopus_id,
                    n.name AS name,
                    n.affiliation AS affiliation,
                    n.country AS country,
                    n.orcid AS orcid
            """,
            orcid = orcid
        ))
    
    db = get_db("rsd")
    results = db.execute_read(work)
    nodes = []
    rels = []
    node_records = []
    nodes_id_in_rel = []

    coauthor_nodes = []
    coauthor_rels = [] 
        
    
    i = 0
    for record in results:
        target = i
        node_records.append(record["doi"])
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

        # if pub, then use scopus id
        coauthor_link = []
        temp_source = []
        
        if record["label"] == "Publication":
            for sco_id in record["scopus_id"]:
                try:
                    source = node_records.index(sco_id)
                except ValueError:
                    node_records.append(sco_id)
                    source = i

                    # name 
                    au_info_results = db.execute_read(get_esc_info_scoid, sco_id)
                    au_name = au_info_results[0]["name"]
                    orcid = au_info_results[0]["orcid"]
                    country = au_info_results[0]["country"]
                    aff = "Netherlands eScience Center"

                    author = {"title": au_name,
                            "scopus_id": sco_id,
                            "orcid": orcid,
                            "country": country,
                            "affiliation": aff,
                            "label": "author",
                            "id": source,
                            "color": "author"}
                    nodes.append(author)
                    coauthor_nodes.append(author)
                    i += 1
                temp_source.append(source)
                nodes_id_in_rel.append(source)
                rels.append({"source": source, "target": target, "doi":record["doi"], "scopus_id": scopus_id, "orcid":orcid})

        else:
            for orcid in record["orcid"]:
                try:
                    source = node_records.index(orcid)
                except ValueError:
                    node_records.append(orcid)
                    source = i

                    # name 
                    au_info_results = db.execute_read(get_esc_info_orcid, orcid)
                    scopus_id = au_info_results[0]["scopus_id"]
                    au_name = au_info_results[0]["name"]
                    country = au_info_results[0]["country"]
                    aff = "Netherlands eScience Center"

                    author = {"title": au_name,
                            "scopus_id": scopus_id,
                            "orcid": orcid,
                            "country": country,
                            "affiliation": aff,
                            "label": "author",
                            "id": source,
                            "color": "author"}
                    nodes.append(author)
                    coauthor_nodes.append(author)
                    i += 1
                temp_source.append(source)
                nodes_id_in_rel.append(source)
                rels.append({"source": source, "target": target, "doi":record["doi"], "scopus_id": scopus_id, "orcid":orcid})
            
        coauthor_link = coauthor_link+list(itertools.combinations(temp_source, 2))

        for l in coauthor_link:
            coauthor_rels.append({"source": l[0], "target": l[1], "doi":record["doi"], "title": record["title"]})

    nodes = get_link_count_of_author(nodes, nodes_id_in_rel)
    coauthor_nodes = get_link_count_of_author(coauthor_nodes, nodes_id_in_rel)
    coauthor_rels = get_link_count_of_rel(coauthor_rels)
        
    return Response(dumps({"nodes": nodes, "links": rels, "coauthor_nodes": coauthor_nodes, "coauthor_links": coauthor_rels}),
                    mimetype="application/json")

if __name__ == "__main__":
    # uri = "bolt://localhost:7687"
    # username = "neo4j"
    # password = "zhiningbai"

    logging.root.setLevel(logging.INFO)
    logging.info("Starting on port %d, database is at %s", port, uri)
    app.run(port=port)

