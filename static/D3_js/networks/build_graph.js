// ########## refresh #############
// remove and initialize the properties of the d3 svg
function refresh(){
    // Remove existing elements
    d3.select("#graph").selectAll("*").remove();
    d3.select('#node-details').style('display', 'none');

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

function refresh_button_situation() {
    selectedNodeTypes = {
        publication: true,
        project: true,
        software: true,
        author: true
    };
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
                .attr("cursor", "pointer")
                .on("click", handleLinkClick);

    // Filter author_nodes and work_nodes
    // var AuthorNodes = graph_node.filter(node => node.label.indexOf("author") != -1);
    // var OtherNodes = graph_node.filter(node => node.label.indexOf("author") == -1);

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
                    else {
                        return d.title.substring(0,15) + '...'
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
        // If it is alrealy clicked
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
        // Or, show the tooltip and its info table
        else {
            addOrRemoveTooltip(d);
            handleNodeClick(d);

            clicked[d.id] = true;
        }
    });

    // 'test' here is the title of every node, it is on the upper layer of the node
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
    force.on("tick", tick).alphaDecay(0.05);

    force.alpha(1).restart();

    if (cluster) {
        // clustering color
        node_topic_color();
    }

    // Reset the link forces and the slider setting
    document.getElementById('mySlider').value = 10;
    document.getElementById('sliderValue').textContent = 10;
    updateSimulationStrength(-10);

    filtered_coauthor_graph_link = graph_link;
    filtered_coauthor_graph_node = graph_node;

    // const renderTime = performance.now() - renderStart;
    // console.log(`Render time: ${renderTime}ms`);
}


function tick() {
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
}


function node_topic_color() {
    // var checkbox = document.getElementById("show_topic_color");
    var nodes = network.selectAll(".node");
    // if (checkbox.checked){
        // Remove the additional classes from the nodes
        nodes.classed('author', false);
        nodes.classed('publication', false);
        nodes.classed('project', false);
        nodes.classed('software', false);
        nodes.classed('author_highlight', false);
        nodes.classed('first_coauthor', false);
        nodes.classed('second_coauthor', false);

        var group_num = Array.apply(null, {length: 7}).map(Number.call, Number);
        
        var colorScale = d3.scaleOrdinal()
            .domain(group_num)
            .range(['#ffadad', '#ffd6a5', '#fdffb6', '#caffbf', '#9bf6ff', '#a0c4ff', '#bdb2ff' ]); // Specify colors for each topic

        var bgColorScale = d3.scaleOrdinal()
            .domain(group_num)
            .range(['#d47777', '#c99c65', '#bdbf67', '#75b567', '#57b4bd', '#668ac4', '#7d71c9' ]);

        nodes.attr('fill', function(d) { if (d.group !== undefined) return colorScale(d.group); 
                                        else {return '#BBB';} });
        nodes.attr('stroke', function(d) { if (d.group !== undefined) return bgColorScale(d.group); 
                                        else {return '#9c9c9c';} });
 
}


function toggleNodeVisibility() {
    // Filter nodes based on the selected types
    var filteredNodes = graph_node.filter(node => selectedNodeTypes[node.label]);
    // Filter links based on the selected types
    // A link is included if both its source and target nodes are included
    let new_graph_Link = graph_link.filter(link => 
        selectedNodeTypes[link.source.label] && selectedNodeTypes[link.target.label]
    );

    // node without links 
    const isolatedNodes = filteredNodes.filter(function(node) {
        return !new_graph_Link.some(function(link) {
            return link.source === node || link.target === node;
        });
    });
    const new_graph_node = filteredNodes.filter(function(node) {
        return !isolatedNodes.includes(node);
    });

    // Because this function works on the 'pub nodes', check the 'show_pub' checkbox by default
    // Set col_count to 1 again
    document.getElementById("show_pub").checked = true;
    document.getElementById("col_count").value = 1;


    refresh();
    build_new_svg(new_graph_node, new_graph_Link);
    

}

function toggleNodeType(nodeType) {
    // Toggle the visibility of the node in the network
    // Flip the selected state of the node type
    selectedNodeTypes[nodeType] = !selectedNodeTypes[nodeType];
    toggleNodeVisibility(nodeType);

    // Change the color of the button to indicate whether the node is visible
    var button = document.getElementById(nodeType + 'Button');
    if (selectedNodeTypes[nodeType]) {          // Visible
        if (nodeType === 'publication')
            button.style.backgroundColor = '#8398cd';
        else if (nodeType === 'project')
            button.style.backgroundColor = '#94bf91';
        else if(nodeType === 'software')
            button.style.backgroundColor = '#c093bd';
    } else {
        button.style.backgroundColor = 'lightgray'; // Hidden
    }
}

function ResetNodeType() {
    // Change the color of the button to make the node is visible
    selectedNodeTypes['publication'] = true;
    var publication_button = document.getElementById('publicationButton');
    publication_button.style.backgroundColor = '#8398cd'

    selectedNodeTypes['project'] = true;
    var project_button = document.getElementById('projectButton');
    project_button.style.backgroundColor = '#94bf91'

    selectedNodeTypes['software'] = true;
    var software_button = document.getElementById('softwareButton');
    software_button.style.backgroundColor = '#c093bd'

}