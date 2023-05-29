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