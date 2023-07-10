// ######## Show selected search field,
// ######## such as: topic, author, publication, institution

function showForm(formId) {
    // Get all forms
    const forms = document.querySelectorAll('.navbar-form');

    // Loop through each form
    forms.forEach(form => {
      if (form.id === formId) {
        form.classList.add('active'); // Show selected form
      } else {
        form.classList.remove('active'); // Hide other forms
      }
    });
  }

// ######## In the Author Search Form, 
// ######## If the name search box is checked, the orcid input item will be hidden,
// ######## If the orcid serach box is checked, the firstname and surname input item will be hidden.
function toggleSearchInput(inputName) {
      var authorSurNameInput = document.getElementById("surname");
      var authorFirstNameInput = document.getElementById("firstname");
      var orcidInput = document.getElementById("orcid");
      
      if (inputName === "author-name") {
        authorSurNameInput.style.display = "block";
        authorFirstNameInput.style.display = "block";
        orcidInput.style.display = "none";
        orcidInput.value = "";
      } else {
        authorSurNameInput.style.display = "none";
        authorFirstNameInput.style.display = "none";
        orcidInput.style.display = "block";
        authorSurNameInput.value = "";
        authorFirstNameInput.value = "";
      }
    }




// ################### keyword search ###################
function field_search(callback){
    
    var form = $('#topic-search');
    var year = form.find("select[name='year']").val();
    var keyword = form.find("input[name=keyword]").val();
    refresh();
    
    d3.json("/topic-search?keyword=" + encodeURIComponent(keyword) + "&year=" + encodeURIComponent(year))
        .then(function(graph){
            if (!graph || graph.length == 0) return;

            graph_node = graph.nodes;
            graph_link = graph.links;
            coauthor_graph_node = graph.coauthor_nodes;
            coauthor_graph_link = graph.coauthor_links;

            if (show_pub) {
                build_new_svg(graph_node, graph_link);
            }
            else {
                build_new_svg(coauthor_graph_node, coauthor_graph_link);
            }
        });
    if (typeof callback === 'function') {
            callback();
        }
    
    
}


// ################### ORCID search ######################
function author_search(){
    // Prevent default form submission action
    // event.preventDefault();   
    var form = $('#author-search');
    var orcid = form.find("input[name='orcid']").val();
    var firstname = form.find("input[name='firstname']").val();
    var surname = form.find("input[name='surname']").val();


    const nameElement = document.getElementById("name-title");
    nameElement.textContent = firstname+' '+surname;

    // Update the ORCID link
    const orcidLinkElement = document.querySelector(".orcid[href]");
    if (orcid) {
        orcidLinkElement.style.display = "inline";
        orcidLinkElement.href = `https://orcid.org/${orcid}`;
    } else {
        orcidLinkElement.style.display = "none";
    }

    // Update the affiliation
    const affiliationElement = document.getElementById("affiliation");
    affiliationElement.textContent = affiliation;
    
    refresh();

    d3.json("/author_search?orcid=" + encodeURIComponent(orcid)+ 
            "&firstname=" + encodeURIComponent(firstname) + 
            "&surname=" + encodeURIComponent(surname) + 
            "&rsd=" + rsd)
        .then(function (graph) {
            if (!graph || graph.length == 0) return;

            // Profile
            author_profile(graph, orcid);

            graph_node = graph.nodes;
            graph_link = graph.links;
            coauthor_graph_node = graph.coauthor_nodes;
            coauthor_graph_link = graph.coauthor_links;

            if (show_pub) {
                build_new_svg(graph_node, graph_link);
            }
            else {
                build_new_svg(coauthor_graph_node, coauthor_graph_link);
            }
            
            ResetNodeType();
            d3.select('#toggle-buttons').style('display', 'block');
            
        });
    return false;
}


// ################### DOI search ######################
function pub_search(){
    var form = $('#pub-search');
    var doi = form.find("input[name='doi']").val();

    refresh();

    d3.json("/pub_search?doi=" + encodeURIComponent(doi))
        .then(function (graph) {
            if (JSON.stringify(graph) === '[]') {
                return false;
            }
            // Profile
            pub_profile(graph,doi);

            graph_node = graph.nodes;
            graph_link = graph.links;

            coauthor_graph_node = graph.coauthor_nodes;
            coauthor_graph_link = graph.coauthor_links;
            
            if (show_pub) {
                build_new_svg(graph_node, graph_link);
            }
            else {
                build_new_svg(coauthor_graph_node, coauthor_graph_link);
            }
            if(rsd) {
                ResetNodeType();
                d3.select('#toggle-buttons').style('display', 'block');
            }
        });
    return false;
}


// ####################### institution search #########################
function aff_search(aff_name, start_year, end_year){
    refresh();

    d3.json("/openalex-aff-search?aff_name=" + aff_name + "&start_year=" + start_year + "&end_year=" + end_year)
    .then(function(graph) {
        if (JSON.stringify(graph) === '[]') {
            return false;
        }

        // make profile
        inst_profile(graph);

        graph_node = graph.nodes;
        graph_link = graph.links;
        coauthor_graph_node = graph.coauthor_nodes;
        coauthor_graph_link = graph.coauthor_links;

        if (show_pub) {
            build_new_svg(graph_node, graph_link);

            var filteredNodes = graph_node.filter(node => node.group !== undefined);
            // Add a custom force to cluster nodes based on their group
            var simulation = d3.forceSimulation(filteredNodes)
                                .force("group", groupForce(filteredNodes).strength(0.1))

            simulation.on("tick", tick).alphaDecay(0.05);
            simulation.alpha(1).restart();
        }
        else {
            build_new_svg(coauthor_graph_node, coauthor_graph_link);
        }

        // CLustering node colors
        node_topic_color();

        // New topic legend
        var topic_colors = ['#ffadad', '#ffd6a5', '#fdffb6', '#caffbf', '#9bf6ff'];

        d3.select('#legend').style('display', 'none');
        d3.select("#legend_list").html("");

        for(var i=0; i<5; i++){
            var list_item = '<li style="margin-bottom:5px;"><span style="background-color:' + topic_colors[i] + 
                '; width:10px; height:10px; display:inline-block; margin-right:5px;"></span>' + topic_names[i] + '</li>';
            d3.select("#legend_list").html(function(d) {
                return d3.select(this).html() + list_item;
            });
        }
            
        d3.select("#topic_cluster_legend").style("display", "block");
    });

    return false;
}

function slider_change(aff_name, size){
    refresh();

    d3.json("/openalex-aff-search-without-profile?aff_name=" + aff_name + "&size=" + size).then(function(graph) {
        // make profile
        if (JSON.stringify(graph) === '[]') {
            return false;
        }
        graph_node = graph.nodes;
        graph_link = graph.links;
        coauthor_graph_node = graph.coauthor_nodes;
        coauthor_graph_link = graph.coauthor_links;

        if (show_pub) {
            build_new_svg(graph_node, graph_link);
        }
        else {
            build_new_svg(coauthor_graph_node, coauthor_graph_link);
        }
    })


}

// ################## Check & highlight node #################
function Find_node(option) {
    // // prevent the default form submission behavior
    // event.preventDefault();

    if (option === "author") {
        for (const i of ["keyword", "doi", "aff"]) {
            document.getElementById(i).value = "";
        }
    }
    else if (option === "publication") {
        for (const i of ["keyword", "orcid", "firstname", "surname", "aff"]) {
            document.getElementById(i).value = "";
        }
    }

    var search_orcid_value = document.getElementById('orcid').value;
    var search_name_value = document.getElementById('firstname').value+' '+document.getElementById('surname').value;
    var search_doi_value = document.getElementById('doi').value;

    var nodeExists = checkNodeExists(search_orcid_value, search_name_value, search_doi_value);

    console.log("nodeExists:" + nodeExists);

    // If the node exists, highlight it; otherwise, show a message
    if (!nodeExists) {
        document.getElementById("error-message").style.visibility = "visible";
        console.log("Sorry, we couldn't find a matching node.")
        setTimeout(hideMessage, 3000);
    } 
}

function hideMessage() {
    document.getElementById("error-message").style.visibility = "hidden"; // Hide the label
}

function checkNodeExists(search_orcid_value, search_name_value, search_doi_value) {
    // Iterate over the nodes in the network
    const NodeToFind = network.selectAll(".node")
                            .filter(function(d) {
                                // Check if the search value matches any property of the node
                                return ((d.doi === search_doi_value && search_doi_value)
                                || (d.orcid === search_orcid_value && search_orcid_value)
                                || (d.title === search_name_value && search_name_value)) 
                            });

    if (NodeToFind.data().length != 0) { // Node exists
        
        handleNodeClick(NodeToFind.data()[0]);
        addOrRemoveTooltip(NodeToFind.data()[0]);

        clicked[NodeToFind.data()[0].id] = true;
        
        return true;
    }
    else {
        return false;
    }

}


// Empty the input field that is not in this stage
function resetFields(option) {
    if (option === "topic") {
        for (const i of ["orcid", "firstname", "surname", "doi", "aff"]) {
            document.getElementById(i).value = "";
        }
    }
    else if (option === "author") {
        for (const i of ["keyword", "doi", "aff"]) {
            document.getElementById(i).value = "";
        }
    }
    else if (option === "publication") {
        for (const i of ["keyword", "orcid", "firstname", "surname", "aff"]) {
            document.getElementById(i).value = "";
        }
    }
    else if (option === "affiliation") {
        for (const i of ["keyword", "orcid", "firstname", "surname", "doi"]) {
            document.getElementById(i).value = "";
        }
    }
}