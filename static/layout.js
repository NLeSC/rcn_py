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


function resetFields(option) {
      if (option === 'topic'){
          document.getElementById("orcid").value = "";

      }
      // else if (option === 'author') {
      //     var formElement = document.getElementById("topic-search");
      //     formElement.reset();
      // }
  }