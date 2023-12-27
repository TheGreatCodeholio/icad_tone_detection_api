// System Select Div Elements
const systemSelect = document.getElementById('system_selection')

//System Form Elements Add/Update/Delete
const addSystemForm = document.getElementById('addSystemForm');


//System Button Elements Add/Update/Delete
const submitAddFormButton = document.getElementById('submitAddForm');

// Load systems on page load
window.addEventListener('load', function () {
    const params = new URLSearchParams(window.location.search);
    const system_id = Number(params.get('system_id'));
    updateSystemSelection(system_id);
});

function updateSystemSelection(system_id = 0) {
    fetch('/api/get_systems')
        .then(response => response.json())
        .then(systems => {
            systemSelect.textContent = ''

            if (system_id === 0) {
                const defaultOption = document.createElement('option');
                defaultOption.value = "";
                defaultOption.textContent = "Select System";
                systemSelect.appendChild(defaultOption);

                systems.result.forEach(system => {
                    const option = document.createElement('option');
                    option.value = system.system_id;
                    option.textContent = system.system_name;
                    systemSelect.appendChild(option);
                });
            } else {
                systems.result.forEach(system => {
                    const option = document.createElement('option');
                    option.value = system.system_id;
                    option.textContent = system.system_name;
                    if (system.system_id === system_id) {
                        option.setAttribute('selected', 'selected');
                        showSystem(system);
                    }
                    systemSelect.appendChild(option);
                });
            }
        })
        .catch(error => {
            console.error('Failed to fetch data:', error);
            // Handle or log the error as needed
        });
}

function querySystem() {
    const systemId = systemSelect.value;

    const params = new URLSearchParams({
        system_id: systemId
    });

    fetch('/api/get_systems?' + params.toString(), {
        method: 'GET'
    })
        .then(response => response.json())
        .then(data => {
            showSystem(data.result)
        });
}

function queryAgency() {
    const systemId = systemSelect.value;

    const params = new URLSearchParams({
        system_id: systemId
    });
    fetch('/api/get_agency?' + params.toString(), {
        method: 'GET'
    })
        .then(response => response.json())
        .then(data => {
            showSystem(data.result)
        });
}

function showSystem(system_data) {
    console.log(system_data)
    let systemConfig = document.getElementById('accordionSystem');
    systemConfig.innerHTML = ''

    system_data = system_data[0]

    // Populate Delete Modal
    const system_delete = document.getElementById('deleteSystemId')
    const del_system_title = document.getElementById('deletesystemNameTitle')

    system_delete.value = system_data.system_id;
    del_system_title.innerText = "Delete " + system_data.system_name + "?";

    const add_agency_system_id = document.getElementById('addAgencySystemId')
    add_agency_system_id.value = system_data.system_id;

    // Create the accordion item container
    let accordionItem = document.createElement('div');
    accordionItem.className = 'accordion-item';

    // Create the accordion header
    let accordionHeader = document.createElement('h2');
    accordionHeader.className = 'accordion-header';
    accordionHeader.id = 'heading_' + system_data.system_id;

    // Create the accordion button
    let accordionButton = document.createElement('button');
    accordionButton.className = 'accordion-button';
    accordionButton.type = 'button';
    accordionButton.setAttribute('data-bs-toggle', 'collapse');
    accordionButton.setAttribute('data-bs-target', '#collapse_' + system_data.system_id);
    accordionButton.setAttribute('aria-expanded', 'false');
    accordionButton.setAttribute('aria-controls', 'collapse_' + system_data.system_id);
    accordionButton.textContent = system_data.system_name;

    // Append the accordion button to the accordion header
    accordionHeader.appendChild(accordionButton);

    // Create the accordion collapse container
    let accordionCollapse = document.createElement('div');
    accordionCollapse.id = 'collapse_' + system_data.system_id;
    accordionCollapse.className = 'accordion-collapse collapse';
    accordionCollapse.setAttribute('aria-labelledby', 'heading_' + system_data.system_id);
    accordionCollapse.setAttribute('data-bs-parent', '#accordionSystem');

    // Create the accordion body
    let accordionBody = document.createElement('div');
    accordionBody.className = 'accordion-body';

    // Create the delete system button
    let sysDeleteButton = document.createElement('button');
    sysDeleteButton.setAttribute("id", "deleteSystemButton");
    sysDeleteButton.setAttribute("type", "button");
    sysDeleteButton.setAttribute("class", "btn btn-danger mb-3");
    sysDeleteButton.setAttribute("data-bs-toggle", "modal");
    sysDeleteButton.setAttribute("data-bs-target", "#deleteSystemModal");
    sysDeleteButton.innerHTML = "Delete System";
    accordionBody.appendChild(sysDeleteButton);

    // Create the add agency button
    let agencyAddButton = document.createElement('button');
    agencyAddButton.setAttribute("id", "addAgencyButton");
    agencyAddButton.setAttribute("type", "button");
    agencyAddButton.setAttribute("class", "btn btn-danger mb-3");
    agencyAddButton.setAttribute("data-bs-toggle", "modal");
    agencyAddButton.setAttribute("data-bs-target", "#addAgencyModal");
    agencyAddButton.innerHTML = "Add Agency";
    accordionBody.appendChild(agencyAddButton);

    // Create the form
    let form = document.createElement('form');
    form.className = 'row g-3';

    // Create the rr system id text input
    let systemNameLabel = document.createElement('label');
    systemNameLabel.className = 'col-md-6 form-label';
    systemNameLabel.textContent = 'System Name:';
    let systemNameInput = document.createElement('input');
    systemNameInput.className = 'col-md-6 form-control';
    systemNameInput.type = 'text';
    systemNameInput.name = 'system_name';
    //systemNameInput.readOnly = true;
    systemNameInput.value = system_data.system_name;
    systemNameLabel.appendChild(systemNameInput);
    form.appendChild(systemNameLabel);

    // Create the rr system id text input
    let systemCountyLabel = document.createElement('label');
    systemCountyLabel.className = 'col-md-6 form-label';
    systemCountyLabel.textContent = 'System County:';
    let systemCountyInput = document.createElement('input');
    systemCountyInput.className = 'col-md-6 form-control';
    systemCountyInput.type = 'text';
    systemCountyInput.name = 'system_county';
    systemCountyInput.value = system_data.system_county;
    systemCountyLabel.appendChild(systemCountyInput);
    form.appendChild(systemCountyLabel);

    // Create the rr system id text input
    let systemStateLabel = document.createElement('label');
    systemStateLabel.className = 'col-md-6 form-label';
    systemStateLabel.textContent = 'System State:';
    let systemStateInput = document.createElement('input');
    systemStateInput.className = 'col-md-6 form-control';
    systemStateInput.type = 'text';
    systemStateInput.name = 'system_state';
    systemStateInput.value = system_data.system_state;
    systemStateLabel.appendChild(systemStateInput);
    form.appendChild(systemStateLabel);

    // Create the rr system id text input
    let systemFIPSLabel = document.createElement('label');
    systemFIPSLabel.className = 'col-md-6 form-label';
    systemFIPSLabel.textContent = 'System State:';
    let systemFIPSInput = document.createElement('input');
    systemFIPSInput.className = 'col-md-6 form-control';
    systemFIPSInput.type = 'text';
    systemFIPSInput.name = 'system_fips';
    systemFIPSInput.value = system_data.system_fips;
    systemFIPSLabel.appendChild(systemFIPSInput);
    form.appendChild(systemFIPSLabel);

    // Create the rr system id text input
    let systemAPILabel = document.createElement('label');
    systemAPILabel.className = 'col-md-6 form-label';
    systemAPILabel.textContent = 'System API Key:';
    let systemAPIInput = document.createElement('input');
    systemAPIInput.className = 'col-md-6 form-control';
    systemAPIInput.type = 'text';
    systemAPIInput.name = 'system_api_key';
    systemNameInput.readOnly = true;
    systemAPIInput.value = system_data.system_api_key;
    systemAPILabel.appendChild(systemAPIInput);
    form.appendChild(systemAPILabel);


    // Create the submit button
    let submitButton = document.createElement('button');
    submitButton.className = 'btn btn-success';
    submitButton.type = 'submit';
    submitButton.textContent = 'Save';

    // Append the submit button to the form
    form.appendChild(submitButton);

    // Append the form to the accordion body
    accordionBody.appendChild(form);

    // Append the accordion body to the accordion collapse container
    accordionCollapse.appendChild(accordionBody);

    // Append the accordion header and collapse to the accordion item
    accordionItem.appendChild(accordionHeader);
    accordionItem.appendChild(accordionCollapse);

    // Append the accordion item to the select element
    systemConfig.appendChild(accordionItem);

}