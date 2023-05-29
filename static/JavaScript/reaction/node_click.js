function handleLinkClick(event, d){
    d3.selectAll('#node_info tbody tr').remove();
    if (d.count) {
        var countRow = d3.select('#node_info tbody')
                .append('tr');
        countRow.append('td')
                .text('Collaboration count');
        countRow.append('td')
                .text(d.count);
    }
    if (show_pub) {
        var doiRow = d3.select('#node_info tbody')
                .append('tr');
        doiRow.append('td')
                .text('DOI');
        doiRow.append('td')
                .text(d.doi);
    }
    else {
        for(let i = 0; i< d.doi.length; i++) {
            var doiRow = d3.select('#node_info tbody')
                    .append('tr');
            doiRow.append('td')
                    .text('DOI');
            doiRow.append('td')
                    .text(d.doi[i]);
                
            if (d.title) {
                var titleRow = d3.select('#node_info tbody')
                        .append('tr');
                titleRow.append('td')
                        .text('Title');
                titleRow.append('td')
                        .text(d.title[i]);
            }
            emptyRow = d3.select('#node_info tbody').append('tr');
            emptyRow .append('td').text('');
            emptyRow.append('td').text('');
        }
    }
    d3.select('#node-details').style('display', 'block');
}


function handleNodeClick(d){
    
        console.log(d.id);
        d3.selectAll('#node_info tbody tr').remove();
        
        if (d.label.indexOf("author") != -1) {
            // Create a new table row for the node label
            var labelRow = d3.select('#node_info tbody')
                .append('tr');
            labelRow.append('td')
                .text('Label');
            labelRow.append('td')
                .text(d.label);
            
            var titleRow = d3.select('#node_info tbody')
                .append('tr');
            titleRow.append('td')
                .text('Name');
            titleRow.append('td')
                .text(d.title);

            var idRow = d3.select('#node_info tbody')
                .append('tr');
            idRow.append('td')
                .text('Scopus id');
            idRow.append('td')
                .text(d.scopus_id);

            var orcidRow = d3.select('#node_info tbody')
                .append('tr');
            orcidRow.append('td')
                .text('ORCID');
            orcidRow.append('td')
                .text(d.orcid);

            // Create a new table row for the node description
            var countryRow = d3.select('#node_info tbody')
                .append('tr');
            countryRow.append('td')
                .text('Country');
            countryRow.append('td')
                .text(d.country);

            var affRow = d3.select('#node_info tbody')
                .append('tr');
            affRow.append('td')
                .text('Affiliation');
            affRow.append('td')
                .text(d.affiliation);
        }
        if (d.label == "publication") {
            // Create a new table row for the node label
            var labelRow = d3.select('#node_info tbody')
                .append('tr');
            labelRow.append('td')
                .text('Label');
            labelRow.append('td')
                .text(d.label);
            
            var titleRow = d3.select('#node_info tbody')
                .append('tr');
            titleRow.append('td')
                .text('Title');
            titleRow.append('td')
                .text(d.title);

            var idRow = d3.select('#node_info tbody')
                .append('tr');
            idRow.append('td')
                .text('DOI');
            idRow.append('td')
                .text(d.doi);

            var subjectRow = d3.select('#node_info tbody')
                .append('tr');
            subjectRow.append('td')
                .text('Subject');
            subjectRow.append('td')
                .text(d.subject);

            var yearRow = d3.select('#node_info tbody')
                .append('tr');
            yearRow.append('td')
                .text('Year');
            yearRow.append('td')
                .text(d.year);
        }
        if (d.label == "project") {
            // Create a new table row for the node label
            var labelRow = d3.select('#node_info tbody')
                .append('tr');
            labelRow.append('td')
                .text('Label');
            labelRow.append('td')
                .text(d.label);
            
            var titleRow = d3.select('#node_info tbody')
                .append('tr');
            titleRow.append('td')
                .text('Title');
            titleRow.append('td')
                .text(d.title);

            var yearRow = d3.select('#node_info tbody')
                .append('tr');
            yearRow.append('td')
                .text('Year');
            yearRow.append('td')
                .text(d.year);
        }
        if (d.label == "software") {
            // Create a new table row for the node label
            var labelRow = d3.select('#node_info tbody')
                .append('tr');
            labelRow.append('td')
                .text('Label');
            labelRow.append('td')
                .text(d.label);
            
            var titleRow = d3.select('#node_info tbody')
                .append('tr');
            titleRow.append('td')
                .text('Title');
            titleRow.append('td')
                .text(d.title);

            var idRow = d3.select('#node_info tbody')
                .append('tr');
            idRow.append('td')
                .text('DOI');
            idRow.append('td')
                .text(d.doi);

            var yearRow = d3.select('#node_info tbody')
                .append('tr');
            yearRow.append('td')
                .text('Year');
            yearRow.append('td')
                .text(d.year);
        }
        // Show the node details table
        
        d3.select('#node-details').style('display', 'block');
              
}

// function for the circle tooltips
function addOrRemoveTooltip(d) {

    // selection.on("click", function(event, d) {
    //     // info presentation
    //     handleNodeClick(d);

        // Tooltip
        
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
            // get unique_id for Database Selecting function 
            if (node_label == "publication" ){
                var unique_id = d.doi;
                // if (d.citation_count != 0) {
                //     node_radius =  6 + Math.log(d.citation_count);
                // }
                // else {node_radius = 6;}
            }
            else if (node_label == "author") {
                if (d.scopus_id) {
                    var unique_id = d.scopus_id; }
                else {
                    var unique_id = d.orcid;
                }

                // node_radius = 5 + Math.log(d.link_num);;
            }
            else if (node_label == "software"){
                var unique_id = d.software_id;
                // node_radius = 5;
            }
            else if (node_label == "project") {
                var unique_id = d.project_id;
                // node_radius = 5;
            }

            // lock node
            d.fx = d.x;
            d.fy = d.y;

            var node_x = d.x;
            var node_y = d.y;

            // present the tooltip of this node
            show_new_tooltip(node_id, unique_id, node_label, node_x, node_y, node_radius);
                    
            
            last_clicked_node = d.id;
            last_d = d;
      
}


// #################### tooltip #####################
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