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
      } else {
        authorSurNameInput.style.display = "none";
        authorFirstNameInput.style.display = "none";
        orcidInput.style.display = "block";
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
    return false;
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

    d3.json("/orcid_search?orcid=" + encodeURIComponent(orcid)+ 
            "&firstname=" + encodeURIComponent(firstname) + 
            "&surname=" + encodeURIComponent(surname) + 
            "&escience=" + escience)
        .then(function (graph) {
            if (!graph || graph.length == 0) return;

            graph_node = graph.nodes;
            graph_link = graph.links;
            coauthor_graph_node = graph.coauthor_nodes;
            coauthor_graph_link = graph.coauthor_links;
            
            search_author_name = graph["search_author_name"];
            works_count = graph['works_count'];
            cited_by_count = graph['cited_by_count'];
            h_index = graph['h_index'];
            ror = graph['ror'];
            search_aff_name = graph["search_aff_name"];
            search_country = graph["search_country"];
            cite_by_year = graph['cite_by_year'];
            concept_score = graph["concept_score"];

            const nameElement = document.getElementById("name-title");
            nameElement.textContent = search_author_name;

            const orcidLinkElement1 = document.getElementById("orcid1");
            const orcidLinkElement2 = document.getElementById("orcid2");
            
            if (orcid) {
                orcidLinkElement1.href = `https://orcid.org/${orcid}`;
                orcidLinkElement2.innerHTML = `https://orcid.org/${orcid}`;
            } else {
                orcidLinkElement1.style.display = "none";
            }

            const rorElement = document.getElementById("ror");
            rorElement.href = ror;
            // Update the affiliation
            const affiliationElement = document.getElementById("affiliation");
            affiliationElement.textContent = search_aff_name+', '+search_country;

            document.getElementById("work-count-value").textContent = works_count;
            document.getElementById("h-index-value").textContent = h_index;
            document.getElementById("citation-count-value").textContent = cited_by_count;

            if (chartexist) {
                myBarChart.data.datasets[0].data = [];
                myPolarChart.data.datasets[0].data = [];
                myBarChart.update();
                myPolarChart.update();
                chartExists = false;
            }
            myBarChart, myPolarChart= set_new_chart(cite_by_year, concept_score);
            chartexist = true;

            document.getElementById("profile").style.visibility = "visible";
            document.getElementById("person_profile").style.display = "block";
            document.getElementById("pub_profile").style.display = "none";
            document.getElementById("aff_profile").style.display = "none";
            document.getElementById("person_table").style.display = "block";
            // document.getElementById("pub_table").style.display = "none";
            d3.select('#node-details').style('display', 'none');

            if (show_pub) {
                build_new_svg(graph_node, graph_link);
            }
            else {
                build_new_svg(coauthor_graph_node, coauthor_graph_link);
            }
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
            graph_node = graph.nodes;
            graph_link = graph.links;

            coauthor_graph_node = graph.coauthor_nodes;
            coauthor_graph_link = graph.coauthor_links;

            // make profile
            if (chartexist) {
                    myBarChart.data.datasets[0].data = [];
                    myPolarChart.data.datasets[0].data = [];
                    myBarChart.update();
                    myPolarChart.update();
                    chartExists = false;
                }
            if ("title" in graph) {
                search_title = graph["title"];
                cited_by_count = graph['cited_by_count'];
                author_string = graph['author_string'];
                author_list = graph['author_list'];
                orcid_list = graph['orcid_list'];
                pub_date = graph['date'];
                source_issn = graph['source_issn'];
                cited_by_count = graph['cited_by_count'];
                cite_by_year = graph['cite_by_year'];
                concept_score = graph["concept_score"];

                const nameElement = document.getElementById("name-title");
                nameElement.textContent = search_title;

                const doiLinkElement1 = document.getElementById("doi1");
                const doiLinkElement2 = document.getElementById("doi2");
                if (doi) {
                    doiLinkElement1.href = "https://doi.org/" + doi;
                    doiLinkElement2.innerHTML = "https://doi.org/" + doi;
                } else {
                    doiLinkElement1.style.display = "none";
                }

                const authorElement = document.getElementById("pub_author_list");
                // refresh the author list
                authorElement.textContent = []
                for (var i = 0; i < author_list.length; i++) {
                    var listItem = document.createElement("a");
                
                    // Create the ORCID icon
                    var orcidIcon = document.createElement("i");
                    orcidIcon.className = "fa-brands fa-orcid";
                    orcidIcon.style.color = "#aecc54";
                
                    // Create the anchor tag with the ORCID URL
                    var anchor = document.createElement("a");
                    if (orcid_list[i]) {
                        anchor.href = orcid_list[i];
                        anchor.target = "_blank"; // Open the link in a new tab
                        anchor.title = orcid_list[i];
                        anchor.appendChild(orcidIcon); // Append the ORCID icon to the anchor
                    }
                
                    // Create the author name text
                    if (i === 0) {
                        var authorName = document.createTextNode(author_list[i]+", ");
                    }
                    else if (i != author_list.length-1) {
                        var authorName = document.createTextNode(" " + author_list[i]+", ");
                    }
                    else {
                        var authorName = document.createTextNode(" " + author_list[i]);
                    }
                
                    // Append the ORCID icon and author name to the list item
                    listItem.appendChild(anchor);
                    listItem.appendChild(authorName);
                
                    // Append the list item to the <ul> element
                    authorElement.appendChild(listItem);
                  }

                // set values in the table
                // document.getElementById("pub-citation-count").textContent = cited_by_count;

                
                myBarChart, myPolarChart= set_new_chart(cite_by_year, concept_score);
                chartexist = true;

                document.getElementById("profile").style.visibility = "visible";
                document.getElementById("person_profile").style.display = "none";
                document.getElementById("pub_profile").style.display = "block";
                document.getElementById("aff_profile").style.display = "none";
                document.getElementById("person_table").style.display = "none";
                // document.getElementById("pub_table").style.display = "none";
            }
            else {
                document.getElementById("profile").style.visibility = "hidden";
            }

            d3.select('#node-details').style('display', 'none');
            
            if (show_pub) {
                build_new_svg(graph_node, graph_link);
            }
            else {
                build_new_svg(coauthor_graph_node, coauthor_graph_link);
            }
        });
    return false;
}


// ####################### institution search #########################
function aff_search(aff_name, start_year, end_year){
    refresh();

    d3.json("/openalex-aff-search?aff_name=" + aff_name + "&start_year=" + start_year + "&end_year=" + end_year)
    .then(function(graph) {
        // make profile
        if (JSON.stringify(graph) === '[]') {
            return false;
        }

        search_title = graph["aff_name"];
        ror = graph["ror"];
        works_count = graph["works_count"]
        cited_by_count = graph['cited_by_count'];
        h_index = graph["h_index"];
        home_page = graph["home_page"];
        city = graph["city"];
        country = graph["country"];
        cite_by_year = graph['cite_by_year'];
        concept_score = graph["concept_score"];

        // const slider = document.getElementById('mySlider');
        // slider.max = works_count;

        const nameElement = document.getElementById("name-title");
        nameElement.textContent = search_title;

        const locationElement = document.getElementById("city-country");
        locationElement.textContent = city+', '+country;

        const doiLinkElement1 = document.getElementById("ror1");
        const doiLinkElement2 = document.getElementById("ror2");
        if (ror) {
            doiLinkElement1.href = ror;
            doiLinkElement2.innerHTML = ror;
        } else {
            doiLinkElement1.style.display = "none";
        }
        
        document.getElementById("work-count-value").textContent = works_count;
        document.getElementById("h-index-value").textContent = h_index;
        document.getElementById("citation-count-value").textContent = cited_by_count;

        
        myBarChart, myPolarChart= set_new_chart(cite_by_year, concept_score);
        chartexist = true;

        document.getElementById("profile").style.visibility = "visible";
        document.getElementById("person_profile").style.display = "none";
        document.getElementById("pub_profile").style.display = "none";
        document.getElementById("aff_profile").style.display = "block";
        document.getElementById("person_table").style.display = "block";
        // document.getElementById("pub_table").style.display = "none";
        d3.select('#node-details').style('display', 'none');

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
    // prevent the default form submission behavior
    event.preventDefault();

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

    console.log(search_orcid_value, search_name_value, search_doi_value);

    var nodeExists = checkNodeExists(search_orcid_value, search_name_value, search_doi_value);

    // If the node exists, highlight it; otherwise, show a message
    if (!nodeExists) {
        document.getElementById("error-message").style.visibility = "visible";
        console.log("Sorry, we couldn't find a matching node.")
        setTimeout(hideMessage, 3000);
    } 
}

function checkNodeExists(search_orcid_value, search_name_value, search_doi_value) {
    // Iterate over the nodes in the network
    const NodeToFind = svg.selectAll(".node")
                            .filter(function(d) {
                                // Check if the search value matches any property of the node
                                return ((d.doi === search_doi_value && search_doi_value)
                                || (d.orcid === search_orcid_value && search_orcid_value)
                                || (d.title === search_name_value && search_name_value)) 
                            });

    console.log(NodeToFind.data());

    if (NodeToFind.data().length != 0) { // Node exists
        
        handleNodeClick(NodeToFind.data()[0]);
        addOrRemoveTooltip(NodeToFind.data()[0]);
        
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