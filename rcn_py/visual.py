import networkx as nx
from pyvis.network import Network

from rcn_py import data_storage


# pyvis
def pyvis_network_by_datafile(orcid_id):
    node_data = data_storage.assign_group_node(orcid_id)
    edge_data, link = data_storage.get_links_from_coauthor_rel(orcid_id)
    all_node_in_link = (
        edge_data["source"].values.tolist() + edge_data["target"].values.tolist()
    )

    # getting weights of links
    weights = []
    for i in link:
        weights.append(link.count(i))
    edge_data["weight"] = weights

    # getting a group id
    groups = node_data.groupby("group")["orcid"].apply(list).reset_index()
    groups["group"] = groups.index

    # finding group id for each node from groups dataframe
    nodes = node_data.merge(groups, how="left", on=["group"])
    nodes["title"] = node_data[["name"]]
    nodes["label"] = node_data[["name"]]
    nodes = nodes.drop("orcid_y", axis=1).set_index("orcid_x")

    colors = [
        "#1f78b4",
        "#e08a34",
        "#643b8a",
        "#3d7a36",
        "#a34b43",
        "#47a68b",
        "blue",
        "red",
        "green",
        "black",
    ]
    node_color = [colors[n] for n in nodes["group"]]
    nodes["color"] = node_color
    # the size of the node could depend on the value, just a test
    nodes["value"] = [all_node_in_link.count(n) for n in node_data["orcid"]]

    # Pyvis network
    N = Network(height=800, width="100%", bgcolor="#222222", font_color="white")
    N.toggle_hide_edges_on_drag(False)
    N.barnes_hut()

    # collecting node attributes for network x
    # node_attrs = nodes.to_dict("index")

    # creating a network x graph from dataframes
    graph = nx.from_pandas_edgelist(edge_data, edge_attr=True)

    d = dict(graph.degree)
    d.update((x, 100 * y) for x, y in d.items())
    nodes["value"] = d.values()

    # collecting node attributes for network x
    node_attrs = nodes.to_dict("index")
    nx.set_node_attributes(graph, node_attrs)

    d = dict(graph.degree)
    d.update((x, 100 * y) for x, y in d.items())
    nx.set_node_attributes(graph, d, "size")

    N.from_nx(graph)
    N.show("test_datafile.html")


# gephi
def gephi_network_by_datafile(orcid_id):
    node_data = data_storage.assign_group_node(orcid_id)
    edge_data, link = data_storage.get_links_from_csv(orcid_id)
    weights = []

    all_node_in_link = (
        edge_data["source"].values.tolist() + edge_data["target"].values.tolist()
    )
    for i in link:
        weights.append(link.count(i))
    edge_data["weight"] = weights

    # getting a group id
    groups = node_data.groupby("group")["orcid"].apply(list).reset_index()
    groups["group"] = groups.index

    # finding group id for each node from groups dataframe
    nodes = node_data.merge(groups, how="left", on=["group"])
    nodes["title"] = node_data[["name"]]
    nodes["label"] = node_data[["name"]]
    nodes = nodes.drop("orcid_y", axis=1).set_index("orcid_x")

    # setting color for each group
    colors = [
        "#1f78b4",
        "#e08a34",
        "#643b8a",
        "#3d7a36",
        "#a34b43",
        "#47a68b",
        "blue",
        "red",
        "green",
        "black",
    ]
    node_color = [colors[n] for n in nodes["group"]]
    nodes["color"] = node_color

    # the size of the node could depend on the value, just a test
    nodes["value"] = [all_node_in_link.count(n) for n in node_data["orcid"]]

    # collecting node attributes for network x
    node_attrs = nodes.to_dict("index")

    # creating a network x graph from dataframes
    G = nx.from_pandas_edgelist(edge_data, edge_attr="weight")
    nx.set_node_attributes(G, node_attrs)

    # ...
    # graph = nx.from_pandas_edgelist(edge_data, edge_attr=True)
    # nx.set_node_attributes(graph, node_attrs)

    
    out_path = orcid_id + ".gexf"

    nx.write_gexf(G, out_path)
