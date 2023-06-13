// ########## refresh #############
// remove and initialize the properties of the d3 svg
function refresh(){
    // Remove existing elements
    d3.select("#graph").selectAll("*").remove();

    // Reset translation and scale variables
    svgTranslate = [0, 0];
    curTranslate = [0, 0];
    svgScale = 1;

    // Reset dragging-related variables
    isDragging = false;
    dx = 0; 
    dy = 0;
    zx = 0; 
    zy = 0;
    
    // Reset clicked and locked nodes
    clicked = {};
    lockked = {};
    last_clicked_node = -1;
    last_d = {};

    // Reset graph-related variables
    maxId = 0;
    graph_node = [];
    graph_link = [];
    
    // Define the SVG canvas
    svg = d3.select("#graph").append("svg")
            .attr("width", width).attr("height", height)
            .attr("position", "absolute")
            .attr("viewBox", `0 0 ${width} ${height}`)
            .attr("pointer-events", "all")
            .call(d3.drag()
                .on("start", canvas_dragstarted)
                .on("drag", canvas_dragged)
                .on("end", canvas_dragended))
            .call(d3.zoom()
                .on("start", zoomstarted)
                .on("zoom", zoomed)
                .on("end", zoomended))
            ;

    // Create group for network elements
    network = svg.append('g').attr('class', 'type1');
    
    // Create group for arc elements
    arcs = svg.append('g').attr('class', 'type2')
            .selectAll("arcs")
            .data([
                { start: 0, end: 1/3, label: "hide", icon: '\uf00d'},
                { start: 1/3, end: 2/3, label: "link", icon: '\uf047'},
                { start: 2/3, end: 1, label: "lock", icon: ['\uf023', '\uf09c'] }
            ])
            .enter();
}

// This function is responsible for building the SVG elements for the graph visualization 
// based on the provided graph_node and graph_link data.
function build_new_svg(graph_node, graph_link) {

    // Set force layout nodes
    force_node = graph_node;

    // Remove fixed positions
    for (var i = 0; i < force_node.length; i++) {
        delete force_node[i].fx;
        delete force_node[i].fy;
    }

    // Set force layout with link force
    force.nodes(force_node)
        .force("link", d3.forceLink(graph_link)
                    .id(function(d) { return d.id; })
                    .distance(d => d.count ? 50/d.count : 50)
                    );

    // Append links to the svg
    const link = network.selectAll(".link")
                .data(graph_link).enter()
                .append("line").attr("class", "link")
                .style("stroke-width", d => d.count ? 1/2*d.count : "0.5px")
                .interrupt('linkTransition')
                .on("click", handleLinkClick);

    // Append nodes to the svg
    const node = network.selectAll(".node")
                .data(graph_node).enter()
                .append("circle")
                .attr("class", function (d) { return "node "+d.color; })
                .attr("r", function (d) { 
                    return d.radius;
                 })
                .attr("cursor", "pointer")
                .style("opacity", 0.8)
                .interrupt('nodeTransition')
                .call(d3.drag()
                    .on("start", node_dragstarted)
                    .on("drag", node_dragged)
                    .on("end", node_dragended));

    // Append labels to the nodes
    const text = network.selectAll("text")
                .data(graph_node).enter()
                .append('text')
                .text(function(d){
                    if (d.label == "author") {
                        return d.title;
                    }
                })
                .style('font-size', d => `${d.radius / 2}px`)
                .style('fill', '#3F3F3F')
                .attr("cursor", "pointer")
                .attr('text-anchor', 'middle')
                .attr('alignment-baseline', 'middle')
                .call(d3.drag()
                    .on("start", node_dragstarted)
                    .on("drag", node_dragged)
                    .on("end", node_dragended));

    // Add title attribute to nodes
    node.append("title")
                .text(function (d) { return d.title; });


    // Get current max node ID (for node expand button)
    graph_node.forEach(node => {
        if (node.id > maxId) {
            maxId = node.id;
        } 
    });  
           
    // Set click event on nodes and labels
    node.on("click", function(event, d) {
        if (clicked[d.id]) {
            arcs.selectAll("path").remove();
            arcs.selectAll("text").remove();
            if(lockked[d.id]){
                d.fx = d.x;
                d.fy = d.y;
            }
            else {
                d.fx = null;
                d.fy = null;
            }
            d3.select('#node-details').style('display', 'none');
            clicked[d.id] = false;
        }
        else {
            addOrRemoveTooltip(d);
            handleNodeClick(d);

            clicked[d.id] = true;
        }
    });
       
    text.on("click", function(event, d) {
        if (clicked[d.id]) {
            arcs.selectAll("path").remove();
            arcs.selectAll("text").remove();
            if(lockked[d.id]){
                d.fx = d.x;
                d.fy = d.y;
            }
            else {
                d.fx = null;
                d.fy = null;
            }
            d3.select('#node-details').style('display', 'none');
            clicked[d.id] = false;
        }
        else {
            addOrRemoveTooltip(d);
            handleNodeClick(d);

            clicked[d.id] = true;
        }
    });
    

    // Force layout tick function
    force.on("tick", function() {
        network.selectAll('.link')
        .attr("x1", function (d) { return d.source.x })
        .attr("y1", function (d) { return d.source.y })
        .attr("x2", function (d) { return d.target.x })
        .attr("y2", function (d) { return d.target.y })
        
        network.selectAll('.node')
        .attr("cx", function (d) { return d.x })
        .attr("cy", function (d) { return d.y })

        network.selectAll('text')
        .attr('x', d => d.x).attr('y', d => d.y);

    }).alphaDecay(0.05);

    force.alpha(1).restart();

}
