
function check_show_pub() {
    var checkbox = document.getElementById("show_pub");
    if (checkbox.checked) {
        // Clear the existing network elements
        // network.selectAll(".node").remove();
        // network.selectAll(".link").remove();
        // network.selectAll("text").remove();
        // maxId = 0;
        // arcs.selectAll("path").remove();
        // arcs.selectAll("text").remove();
        refresh();

        show_pub = true;

        ResetNodeType();

        // Make the selection disabled, 
        // because networks with publications only contain Author->Publication links
        document.getElementById('col_count').value = 1;
        document.getElementById('col_count').disabled = true;

        // Show SVG using data with publication nodes
        build_new_svg(graph_node, graph_link);
        if (cluster) {

            // Make the nodes in the same group be together
            var filteredNodes = graph_node.filter(node => node.group !== undefined);
            // Add a custom force to cluster nodes based on their group
            var simulation = d3.forceSimulation(filteredNodes)
                            .force("group", groupForce(filteredNodes).strength(0.1))
            simulation.on("tick", tick).alphaDecay(0.05);
            simulation.alpha(1).restart();
        }
       
    } else {
        // Clear the existing network elements
        // network.selectAll(".node").remove();
        // network.selectAll(".link").remove();
        // network.selectAll("text").remove();
        // maxId = 0;
        // arcs.selectAll("path").remove();
        // arcs.selectAll("text").remove();
        refresh();

        show_pub = false;
        document.getElementById('col_count').disabled = false;
        // Show SVG using data without publication nodes
        build_new_svg(coauthor_graph_node, coauthor_graph_link);
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
        // network.selectAll(".node").remove();
        // network.selectAll(".link").remove();
        // network.selectAll("text").remove();
        // maxId = 0;
        
        filtered_coauthor_graph_node = filteredCoauthorNodes.filter(function(node) {
            return !isolatedNodes.includes(node);
        });
        filtered_coauthor_graph_link = filteredCoauthorLinks;
        
        refresh();
        // build new network
        build_new_svg(filtered_coauthor_graph_node, filtered_coauthor_graph_link);

        // remove the tooltip
        arcs.selectAll("path").remove();
        arcs.selectAll("text").remove();

    }

}

// ######################### Slider ############################
function updateSimulationStrength(strength) {
    force.force("charge", d3.forceManyBody().strength(strength))

    // Add an additional force for nodes without links
    // var repulsiveForce = d3.forceManyBody()
    //             .strength(strength*2)        
    // force.force("repulsion", repulsiveForce);
    
    force.on("tick", tick).alphaDecay(0.05);   
    force.alpha(1).restart(); // Restart the simulation to apply the changes
}

const slider = document.getElementById('mySlider');
    
slider.addEventListener('input', function(){
    const sliderValue = document.getElementById('sliderValue');
    sliderValue.textContent = slider.value;
})
slider.addEventListener('change', function() {
    slider_value = slider.value * -1;
    // Handle the slider value change
    
    console.log('Slider value:', slider_value);
    updateSimulationStrength(slider_value);
    // var aff_name = document.getElementById("name-title").textContent;
    // slider_change(aff_name, slider_value);
    
});
