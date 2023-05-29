
function check_show_pub() {
    var checkbox = document.getElementById("show_pub");
    if (checkbox.checked) {
        network.selectAll(".node").remove();
        network.selectAll(".link").remove();
        network.selectAll("text").remove();
        maxId = 0;
        arcs.selectAll("path").remove();
        arcs.selectAll("text").remove();

        show_pub = true;
        build_new_svg(graph_node, graph_link);
       
    } else {
        network.selectAll(".node").remove();
        network.selectAll(".link").remove();
        network.selectAll("text").remove();
        maxId = 0;
        arcs.selectAll("path").remove();
        arcs.selectAll("text").remove();

        show_pub = false;
        build_new_svg(coauthor_graph_node, coauthor_graph_link);
    }
}

function node_topic_color() {
    var checkbox = document.getElementById("show_topic_color");
    var nodes = network.selectAll(".node");
    if (checkbox.checked){
        // Remove the additional classes from the nodes
        nodes.classed('author', false);
        nodes.classed('publication', false);
        nodes.classed('project', false);
        nodes.classed('software', false);
        nodes.classed('author_highlight', false);
        nodes.classed('first_coauthor', false);
        nodes.classed('second_coauthor', false);

        var group_num = Array.apply(null, {length: 7}).map(Number.call, Number)
        
        var colorScale = d3.scaleOrdinal()
            .domain(group_num)
            .range(['#ffadad', '#ffd6a5', '#fdffb6', '#caffbf', '#9bf6ff', '#a0c4ff', '#bdb2ff' ]); // Specify colors for each topic

        nodes.attr('fill', function(d) { if (d.group) return colorScale(d.group); 
                                        else {return '#9c9c9c';} });
    } 
    else {
        nodes.attr("class", function (d) { return "node "+d.color; })
    }
}

function collaMin() {
    var collaboration_min = document.getElementById("col_count").value;
    col_min = Number(collaboration_min)
    if (show_pub == false) {
        filteredCoauthorNodes = coauthor_graph_node;
        const filteredCoauthorLinks = coauthor_graph_link.filter(link => link.count >= col_min);
        // filter isolated nodes that do not have any links
        const isolatedNodes = filteredCoauthorNodes.filter(function(node) {
            return !filteredCoauthorLinks.some(function(link) {
                return link.source === node || link.target === node;
            });
        });
        // delete the original canvas
        network.selectAll(".node").remove();
        network.selectAll(".link").remove();
        network.selectAll("text").remove();
        maxId = 0;

        
        filteredCoauthorNodes = filteredCoauthorNodes.filter(function(node) {
            return !isolatedNodes.includes(node);
        });
        // coauthor_graph_link  = filteredCoauthorLinks;
        // console.log(graph_node);
        // build new network
        build_new_svg(filteredCoauthorNodes, filteredCoauthorLinks)

        // remove the tooltip
        arcs.selectAll("path").remove();
        arcs.selectAll("text").remove();

    }

}
