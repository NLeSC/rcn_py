function author_profile(graph, orcid) {

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
    d3.select('#node-details').style('display', 'none');
}

function pub_profile(graph, doi) {
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
}

function inst_profile(graph) {
    // Extract profile information
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

    // Update the profile elements with the retrieved information
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

    // Update or create the bar and polar charts
    if (chartexist) {
                myBarChart.data.datasets[0].data = [];
                myPolarChart.data.datasets[0].data = [];
                myBarChart.update();
                myPolarChart.update();
                chartExists = false;
    }
    myBarChart, myPolarChart= set_new_chart(cite_by_year, concept_score);
    chartexist = true;

    // Show the profile elements and hide others
    document.getElementById("profile").style.visibility = "visible";
    document.getElementById("person_profile").style.display = "none";
    document.getElementById("pub_profile").style.display = "none";
    document.getElementById("aff_profile").style.display = "block";
    document.getElementById("person_table").style.display = "block";
}