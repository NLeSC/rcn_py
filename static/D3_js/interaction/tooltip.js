// ############# Determine whether to display a tooltip ##############
function addOrRemoveTooltip(d) {
        
            // If click another node, hide the previous tootip
            if (last_clicked_node && last_clicked_node != d.id) {
                clicked[last_clicked_node] = false;

                if(lockked[last_clicked_node]){
                    last_d.fx = last_d.x;
                    last_d.fy = last_d.y;
                }
                else {
                    last_d.fx = null;
                    last_d.fy = null;
                }
                arcs.selectAll("path").remove();
                arcs.selectAll("text").remove();
            }

            var node_id = d.id;
            var node_label = d.label;
            var node_radius = d.radius;

            // Get unique_id for Database Selecting function
            var unique_id;
            if (node_label == "publication" ){
                unique_id = d.doi;
            }
            else if (node_label == "author") {
                if (d.scopus_id) {
                    unique_id = d.scopus_id; }
                else {
                    unique_id = d.orcid;
                }
            }
            else if (node_label == "software"){
                unique_id = d.software_id;
            }
            else if (node_label == "project") {
                unique_id = d.project_id;
            }

            // fix the position of the node
            d.fx = d.x;
            d.fy = d.y;

            var node_x = d.x;
            var node_y = d.y;

            console.log("position(x,y):"+ node_x,node_y);

            // Present the tooltip of this node
            show_new_tooltip(node_id, unique_id, node_label, node_x, node_y, node_radius);
                    
            last_clicked_node = d.id;
            last_d = d;
      
}


// #################### tooltip settings #####################
function show_new_tooltip(node_id, unique_id, node_label,node_x, node_y, node_radius){
        arcs.selectAll("path").remove();
        arcs.selectAll("text").remove();

        var icons = arcs.append('text')
                                .attr("font-family", "FontAwesome")
                                .attr("text-anchor", "middle")
                                .attr("font-size", "10px")
                                .attr("x", d=>node_x + (node_radius+7) * Math.cos((d.start + d.end-1/2) * Math.PI))
                                .attr("y", d=>node_y+3 + (node_radius+7) * Math.sin((d.start + d.end-1/2) * Math.PI))
                                .text(function(d) { 
                                    if (d.label == 'lock'){
                                        if (lockked[node_id])
                                            return d.icon[1];
                                        else 
                                            return d.icon[0];
                                    }
                                    else{
                                        return d.icon;
                                    } })
                                ; 
        var arc = d3.arc()
                .innerRadius(node_radius+1).outerRadius(node_radius+14);
        arcs.append("path")
                .attr("d", d => arc({
                            "startAngle": d.start * 2 * Math.PI + 0.02,
                            "endAngle": d.end * 2 * Math.PI - 0.02
                        }))    
                .attr("transform", `translate(${node_x},${node_y})`)
                .attr("fill", "lightgrey")
                .style("opacity", 0.5)

                .on("mouseover", function(event, d) {
                    // change the style of the button
                    d3.select(this)
                    .style("opacity", 0.2);
                })
                .on("mouseout", function(event, d) {
                    // restore the style of the button
                    d3.select(this)
                    .style("opacity", 0.5);
                })
                .on("click", function(event, d){
                    if (d.label == "hide") {
                        d3.select(this).style("opacity", 0.5);
                        hide_node(node_id);
                    }
                    if (d.label == "lock") {
                        d3.select(this).style("opacity", 0.5);
                        node_lock_unlock(node_id);
                        icons.text(function(d) { 
                                    if (d.label == 'lock'){
                                        if (lockked[node_id])
                                            return d.icon[1];
                                        else 
                                            return d.icon[0];
                                    }
                                    else{
                                        return d.icon;
                                    } })
                                ; 
                    }
                    if (d.label == "link") {
                        d3.select(this).style("opacity", 0.5);
                        show_all_link(unique_id, node_label, node_id);
                    }        
                });
    }



// ################## The following is the three functions of tooltips #############

// fix the position of the node.
// when do node_drag() function or others, the lokked[node_id] will be checked,
// If ond node is locked, the fx and fy of this node is fixed.
function node_lock_unlock(node_id) {
    // Because when a node is clicked, the position of the node is fixed,
    // so we only need to save its current state, which will be checked when the node is free.
    if (lockked[node_id]) {
        lockked[node_id] = false;
    }
    else {
        lockked[node_id] = true;
    }
}


function hide_node(node_id) {
    // Remove instead of hide

    // Select the node with the given ID
    // Select all links with the given node ID as the source or target

    const filteredNodes = graph_node.filter(node => node.id !== node_id);
    const filteredLinks = graph_link.filter(link => link.source.id !== node_id && link.target.id !== node_id);
    const filteredCoauthorNodes = filtered_coauthor_graph_node.filter(node => node.id !== node_id);
    const filteredCoauthorLinks = filtered_coauthor_graph_link.filter(link => link.source.id !== node_id && link.target.id !== node_id);

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
    filtered_coauthor_graph_node = filteredCoauthorNodes.filter(function(node) {
        return !isolatedCoauthorNodes.includes(node);
    });
    filtered_coauthor_graph_link  = filteredCoauthorLinks;

    // build new network
    if (show_pub) {
        build_new_svg(graph_node, graph_link)
    }
    else {
        build_new_svg(filtered_coauthor_graph_node, filtered_coauthor_graph_link)
    }

    if (cluster) {

        // Make the nodes in the same group be together
        var PubNodes = graph_node.filter(node => node.group !== undefined);
        // Add a custom force to cluster nodes based on their group
        var simulation = d3.forceSimulation(PubNodes)
                        .force("group", groupForce(PubNodes).strength(0.1))
        simulation.on("tick", tick).alphaDecay(0.05);
        simulation.alpha(1).restart();
    }

    // If we hide the node, then remove the tooltip of this node.
    arcs.selectAll("path").remove();
    arcs.selectAll("text").remove();
    d3.select('#node-details').style('display', 'none');

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
        d3.select('#node-details').style('display', 'none');
        
        graph_node = graph_node.concat(links.nodes);
        graph_link = graph_link.concat(links.links);
        filtered_coauthor_graph_node = filtered_coauthor_graph_node.concat(links.coauthor_nodes);
        filtered_coauthor_graph_link = filtered_coauthor_graph_link.concat(links.coauthor_links);

        if (show_pub) {
            build_new_svg(graph_node, graph_link);
        }
        else {
            build_new_svg(filtered_coauthor_graph_node, filtered_coauthor_graph_link);
        }

        if (cluster) {

            // Make the nodes in the same group be together
            var filteredNodes = graph_node.filter(node => node.group !== undefined);
            // Add a custom force to cluster nodes based on their group
            var simulation = d3.forceSimulation(filteredNodes)
                            .force("group", groupForce(filteredNodes).strength(0.1))
            simulation.on("tick", tick).alphaDecay(0.05);
            simulation.alpha(1).restart();
        }
        
    });
}