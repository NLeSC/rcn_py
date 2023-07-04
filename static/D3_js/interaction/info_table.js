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

        if(d.author_name) {
            var nameRow = d3.select('#node_info tbody')
                .append('tr');
            nameRow.append('td')
                    .text('Author name');
            nameRow.append('td')
                    .text(d.author_name);
        }
    }
    else {
        for(let i = 0; i< d.doi.length; i++) {
            emptyRow = d3.select('#node_info tbody').append('tr');
            emptyRow.append('td').text('');
            emptyRow.append('td').text('');

            if(d.doi[i]){
                var doiRow = d3.select('#node_info tbody')
                        .append('tr');
                doiRow.append('td')
                        .text('DOI');
                doiRow.append('td')
                        .text(d.doi[i]);
            }
                
            if (d.title) {
                var titleRow = d3.select('#node_info tbody')
                        .append('tr');
                titleRow.append('td')
                        .text('Title');
                titleRow.append('td')
                        .text(d.title[i]);
            }
            
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

            if(d.scopus_id) {
                var idRow = d3.select('#node_info tbody')
                    .append('tr');
                idRow.append('td')
                    .text('Scopus id');
                idRow.append('td')
                    .text(d.scopus_id);
            }

            if(d.orcid) {
                var orcidRow = d3.select('#node_info tbody')
                    .append('tr');
                orcidRow.append('td')
                    .text('ORCID');
                orcidRow.append('td')
                    .text(d.orcid);
            }

            if(d.openalex_id) {
                var idRow = d3.select('#node_info tbody')
                    .append('tr');
                idRow.append('td')
                    .text('OpenAlex id');
                idRow.append('td')
                    .text(d.openalex_id);
            }

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

            if (d.hasOwnProperty('group')) {
                var subjectRow = d3.select('#node_info tbody')
                    .append('tr');
                subjectRow.append('td')
                    .text('Group');
                subjectRow.append('td')
                    .text("Cluster "+ d.group + ": " +d.topic_name);
            }

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

