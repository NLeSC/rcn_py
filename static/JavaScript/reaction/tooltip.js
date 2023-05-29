// fix the position of the node.
// when do node_drag() function or others, the lokked[node_id] will be checked,
// If ond node is locked, the fx and fy of this node is fixed.
function node_lock_unlock(node_id) {
    if (lockked[node_id]) {
        lockked[node_id] = false;
    }
    else {
        lockked[node_id] = true;
    }
}

function hide_node(node_id) {
    // Select the node with the given ID
    // Select all links with the given node ID as the source or target
    const filteredNodes = graph_node.filter(node => node.id !== node_id);
    const filteredLinks = graph_link.filter(link => link.source.id !== node_id && link.target.id !== node_id);
    const filteredCoauthorNodes = coauthor_graph_node.filter(node => node.id !== node_id);
    const filteredCoauthorLinks = coauthor_graph_link.filter(link => link.source.id !== node_id && link.target.id !== node_id);

    // filter isolated nodes that do not have any links
    const isolatedNodes = filteredNodes.filter(function(node) {
        return !filteredLinks.some(function(link) {
            return link.source === node || link.target === node;
        });
    });
    const isolatedCoauthorNodes = filteredCoauthorNodes.filter(function(node) {
        return !filteredCoauthorLinks.some(function(link) {
            return link.source === node || link.target === node;
        });
    });

    // delete the original canvas, and show the new one 
    network.selectAll(".node").remove();
    network.selectAll(".link").remove();
    network.selectAll("text").remove();
    // The function of maxId is like its name, 
    // which helps to create new nodes with id = maxId++, making the ids not duplicate
    maxId = 0;

    // Remove isolated nodes from the nodes array
    graph_node = filteredNodes.filter(function(node) {
        return !isolatedNodes.includes(node);
    });
    graph_link = filteredLinks;
    coauthor_graph_node = filteredCoauthorNodes.filter(function(node) {
        return !isolatedCoauthorNodes.includes(node);
    });
    coauthor_graph_link  = filteredCoauthorLinks;
    // build new network
    if (show_pub) {
        build_new_svg(graph_node, graph_link)
    }
    else {
        build_new_svg(coauthor_graph_node, coauthor_graph_link)
    }
    // If we hide the node, then remove the tooltip of this node.
    arcs.selectAll("path").remove();
    arcs.selectAll("text").remove();

}

// Show all the related links and linked nodes of the selected node. 
// 
function show_all_link(unique_id, node_label, node_id) {

    const linksToFilter = svg.selectAll(".link")
                            .filter(function(d) {
                                return d.source.id === node_id || d.target.id === node_id;
                            });
    if (node_label == "publication") {
        // linkList: record the unique_ids (such as ORCID, DOI, scopus_id..) of existing linked coauthor nodes,
        // which would be used to fetch data from databases.
        var linkList = linksToFilter.data().map(function(d) {
            return d.scopus_id;
        });
        // coauthor_id: record the ids of existing linked coauthor nodes.
        var coauthor_id = linksToFilter.data().map(function(d) {
            if (d.source.id === node_id)
                return d.target.id;
            else if(d.target.id === node_id)
                return d.source.id;
        });
    }
    else if (node_label == "author") {
        var linkList = linksToFilter.data().map(function(d) {
            return d.doi;
        });
        var coauthor_id = node_id;
    }
    else {
        var linkList = linksToFilter.data().map(function(d) {
            return d.orcid;
        });
        var coauthor_id = linksToFilter.data().map(function(d) {
            return d.index;
        });
    }

    d3.json("/show_link?unique_id=" + encodeURIComponent(unique_id) 
    + "&label=" + encodeURIComponent(node_label)
    + "&node_id=" + encodeURIComponent(node_id)
    + "&maxId=" + encodeURIComponent(maxId)
    + "&linkList=" + encodeURIComponent(linkList)
    + "&coauthorList=" + encodeURIComponent(coauthor_id)
    )
    .then(function(links){
        network.selectAll(".node").remove();
        network.selectAll(".link").remove();
        network.selectAll("text").remove();
        maxId = 0;
        arcs.selectAll("path").remove();
        arcs.selectAll("text").remove();
        
        graph_node = graph_node.concat(links.nodes);
        graph_link = graph_link.concat(links.links);
        coauthor_graph_node = coauthor_graph_node.concat(links.coauthor_nodes);
        coauthor_graph_link = coauthor_graph_link.concat(links.coauthor_links);

        if (show_pub) {
            build_new_svg(graph_node, graph_link);
        }
        else {
            build_new_svg(coauthor_graph_node, coauthor_graph_link);
        }
        
    });
}