function node_dragstarted(event) {
    if (!event.active) force.alphaTarget(0.05).restart();
    event.subject.fx = event.subject.x;
    event.subject.fy = event.subject.y;
}

function node_dragged(event, d) {
    event.subject.fx = event.x;
    event.subject.fy = event.y;
    if (clicked[d.id]) {
        var node_id = d.id;
        var node_label = d.label;
        var node_radius = d.radius;
        if (node_label == "publication"){
            var unique_id = d.doi;
        }
        else if (node_label == "author") {
            if (d.scopus_id) {
                var unique_id = d.scopus_id; }
            else {
                var unique_id = d.orcid; }
        }
        else if (node_label == "software"){
            var unique_id = d.software_id;
        }
        else if (node_label == "project"){
            var unique_id = d.project_id;
        }
        // If a node is moving, its tooltip and icons will move along with it     
        show_new_tooltip(node_id, unique_id, node_label, event.x, event.y, node_radius);
    }
}
      
function node_dragended(event, d) {
    if (!event.active) force.alphaTarget(0);
    if (lockked[d.id] || clicked[d.id]) {
        event.subject.fx = event.x;
        event.subject.fy = event.y;}
    else{
        event.subject.fx = null;
        event.subject.fy = null;
    }
    force.alphaTarget(0.0).restart();
}