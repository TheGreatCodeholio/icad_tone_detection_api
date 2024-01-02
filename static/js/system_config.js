// System Select Div Elements
const systemSelect = document.getElementById('system_selection')

//System Form Elements Add/Update/Delete
const addSystemForm = document.getElementById('addSystemForm');


//System Button Elements Add/Update/Delete
const submitAddFormButton = document.getElementById('submitAddForm');

//Alert Area
const alertDiv = document.getElementById('nav_alert');

// Load systems on page load
window.addEventListener('load', function () {
    const params = new URLSearchParams(window.location.search);
    const system_id = Number(params.get('system_id'));
    updateSystemSelection(system_id);
});

function createElementWithAttributes(tag, attributes) {
    let element = document.createElement(tag);
    for (let key in attributes) {
        if (key === 'innerHTML') {
            element.innerHTML = attributes[key];
        } else {
            element.setAttribute(key, attributes[key]);
        }
    }
    return element;
}

function createInputFormGroup(labelText, inputType, name, value, readOnly = false) {
    let label = createElementWithAttributes('label', {className: 'col-md-6 form-label', innerHTML: labelText});
    let input = createElementWithAttributes('input', {
        className: 'col-md-6 form-control',
        type: inputType,
        name: name,
        value: value,
        readOnly: readOnly
    });
    label.appendChild(input);
    return label;
}

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
                    }
                    systemSelect.appendChild(option);
                });
                querySystem();
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
        system_id: systemId,
        with_agencies: true
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

    showAgencies(system_data);
}

function showAgencies(system_data) {
    let agencyConfig = document.getElementById('accordionAgency')
    system_data.agencies.forEach(agency => {
        console.log(agency)
        // Create the accordion item container
        let accordionItem = document.createElement('div');
        accordionItem.className = 'accordion-item ag_config_item';

        // Create the accordion header
        let accordionHeader = document.createElement('h2');
        accordionHeader.className = 'accordion-header';
        accordionHeader.id = 'heading_' + agency.agency_id;

        // Create the accordion button
        let accordionButton = document.createElement('button');
        accordionButton.className = 'accordion-button';
        accordionButton.type = 'button';
        accordionButton.setAttribute('data-bs-toggle', 'collapse');
        accordionButton.setAttribute('data-bs-target', '#collapse_' + agency.agency_id);
        accordionButton.setAttribute('aria-expanded', 'false');
        accordionButton.setAttribute('aria-controls', 'collapse_' + agency.agency_id);
        accordionButton.textContent = agency.agency_name;

        // Append the accordion button to the accordion header
        accordionHeader.appendChild(accordionButton);

        // Create the accordion collapse container
        let accordionCollapse = document.createElement('div');
        accordionCollapse.id = 'collapse_' + agency.agency_id;
        accordionCollapse.className = 'accordion-collapse collapse';
        accordionCollapse.setAttribute('aria-labelledby', 'heading_' + agency.agency_id);
        accordionCollapse.setAttribute('data-bs-parent', '#accordionAgencies');

        // Create the accordion body
        let accordionBody = document.createElement('div');
        accordionBody.className = 'accordion-body';

        //Create Form
        let form = document.createElement('form');
        form.id = 'agency_input_form_' + agency.agency_id;
        form.method = 'post';
        form.className = 'row g-3';

        // Hidden input for system_id
        let hiddenInput = document.createElement('input');
        hiddenInput.setAttribute('type', 'hidden');
        hiddenInput.className = 'form-control';
        hiddenInput.id = 'addAgencySystemId_' + agency.agency_id;
        hiddenInput.name = 'system_id';
        hiddenInput.value = agency.system_id
        form.appendChild(hiddenInput);

        // Create the main div container
        let agencyInputDiv = document.createElement('div');
        agencyInputDiv.id = 'agency_input_div_' + agency.agency_id;
        form.appendChild(agencyInputDiv);

        // Create the ul element for tabs
        let tabsUl = document.createElement('ul');
        tabsUl.className = 'nav nav-tabs';
        tabsUl.id = 'agency_tabs_' + agency.agency_id;
        tabsUl.setAttribute('role', 'tablist');
        agencyInputDiv.appendChild(tabsUl);

        // Array of tab names
        let tabNames = ['Agency', 'QCII Tones', 'Emails', 'MQTT', 'Pushover', 'Facebook'];

        // Create li and button elements for each tab
        tabNames.forEach((tabName, index) => {
            let li = document.createElement('li');
            li.className = 'nav-item';
            li.setAttribute('role', 'presentation');

            let button = document.createElement('button');
            button.className = 'conf-link nav-link' + (index === 0 ? ' active' : '');
            button.id = tabName.toLowerCase().replace(/\s+/g, '') + '-tab_' + agency.agency_id;
            button.setAttribute('data-bs-toggle', 'tab');
            button.setAttribute('data-bs-target', '#' + tabName.toLowerCase().replace(/\s+/g, '') + '-tab-pane_' + agency.agency_id);
            button.setAttribute('type', 'button');
            button.setAttribute('role', 'tab');
            button.setAttribute('aria-controls', tabName.toLowerCase().replace(/\s+/g, '') + '-tab-pane_' + agency.agency_id);
            button.setAttribute('aria-selected', index === 0 ? 'true' : 'false');
            button.textContent = tabName;

            li.appendChild(button);
            tabsUl.appendChild(li);
        });

        // Create the tab-content div
        let tabContentDiv = document.createElement('div');
        tabContentDiv.className = 'tab-content';
        tabContentDiv.id = 'agencyTabContent_' + agency.agency_id;
        agencyInputDiv.appendChild(tabContentDiv);

        let tabPanes = [
            {
                id: 'agency-tab-pane',
                label: 'Agency Configuration',
                fields: [
                    {
                        label: 'Agency Name',
                        id: 'agency_name',
                        tooltip: 'Agency Name',
                        type: 'text',
                        class: 'w-75',
                        required: true
                    },
                    {
                        label: 'Agency Code',
                        id: 'agency_code',
                        tooltip: 'Station Number Or Agency Abbreviation',
                        type: 'text',
                        class: 'w-75'
                    }
                ]
            },
            {
                id: 'qciitones-tab-pane',
                label: 'Quick Call Configuration',
                fields: [
                    {
                        label: 'Tone A Frequency',
                        id: 'a_tone',
                        tooltip: 'Quick Call II Tone A',
                        type: 'text',
                        class: 'w-75',
                        required: true
                    },
                    {
                        label: 'Tone B Frequency',
                        id: 'b_tone',
                        tooltip: 'Quick Call II Tone B',
                        type: 'text',
                        class: 'w-75',
                        required: true
                    },
                    {
                        label: 'Tone Match Tolerance',
                        id: 'tone_tolerance',
                        tooltip: 'plus/minus tolerance in decimal form applied to a frequency to determine a match. 0.05 is 5%',
                        type: 'text',
                        class: 'w-50',
                        required: true
                    },
                    {
                        label: 'Agency Ignore Time',
                        id: 'ignore_time',
                        tooltip: 'Ignore time in seconds after a successful match.',
                        type: 'text',
                        class: 'w-75',
                        required: true
                    }
                ]
            },
            {
                id: 'emails-tab-pane',
                label: 'Alert Emails',
                fields: [
                    {
                        label: 'Alert Email Addresses',
                        id: 'alert_emails',
                        tooltip: 'Comma separated list of Alert Emails',
                        type: 'text',
                        class: 'w-50'
                    },
                    {
                        label: 'Alert Email Subject Override',
                        id: 'alert_email_subject',
                        tooltip: 'Override Global Alert Email Subject',
                        type: 'text',
                        class: 'w-100'
                    },
                    {
                        label: 'Alert Email Body',
                        id: 'alert_email_body',
                        tooltip: 'Override Global Alert Email Body',
                        type: 'textarea',
                        class: 'w-100'
                    }
                ]
            },
            {
                id: 'mqtt-tab-pane',
                label: 'MQTT Configuration',
                fields: [
                    {
                        label: 'MQTT Topic',
                        id: 'mqtt_topic',
                        tooltip: 'MQTT topic to publish to. Example: dispatch/siren',
                        type: 'text',
                        class: 'w-50'
                    },
                    {
                        label: 'MQTT Start Message',
                        id: 'mqtt_start_alert_message',
                        tooltip: 'First message sent to MQTT topic.',
                        type: 'text',
                        class: 'w-50'
                    },
                    {
                        label: 'MQTT End Message',
                        id: 'mqtt_end_alert_message',
                        tooltip: 'Second message sent to MQTT topic.',
                        type: 'text',
                        class: 'w-50'
                    },
                    {
                        label: 'MQTT Interval Time',
                        id: 'mqtt_message_interval',
                        tooltip: 'Interval in seconds between start and end MQTT message.',
                        type: 'text',
                        class: 'w-50'
                    }
                ]
            },
            {
                id: 'pushover-tab-pane',
                label: 'Pushover Configuration',
                fields: [
                    {
                        label: 'Pushover Group Token',
                        id: 'pushover_group_token',
                        tooltip: 'Group token from Pushover group for this agency.',
                        type: 'text',
                        class: 'w-50'
                    },
                    {
                        label: 'Pushover App Token',
                        id: 'pushover_app_token',
                        tooltip: 'Token from Pushover application for this agency.',
                        type: 'text',
                        class: 'w-50'
                    },
                    {
                        label: 'Pushover Message Override Subject',
                        id: 'pushover_subject_override',
                        tooltip: 'Override Global Subject for Pushover Message.',
                        type: 'text',
                        class: 'w-50'
                    },
                    {
                        label: 'Pushover Message HTML',
                        id: 'pushover_body_override',
                        tooltip: 'Override Global Message Body for Pushover.',
                        type: 'textarea',
                        class: 'w-50'
                    },
                    {
                        label: 'Pushover Alert Sound',
                        id: 'pushover_sound_override',
                        tooltip: 'Override Global Alert Sound for Pushover Notification.',
                        type: 'text',
                        class: 'w-50'
                    }
                ]
            },
            {
                id: 'facebook-tab-pane',
                label: 'Facebook Configuration',
                fields: [
                    {
                        label: 'Posting to Facebook',
                        id: 'enable_facebook_post',
                        tooltip: 'Post Detection To Facebook.',
                        type: 'select',
                        class: 'w-50',
                        options: [{value: '1', text: 'Enabled'}, {value: '0', text: 'Disabled', selected: true}]
                    }
                ]
            }
        ];

        // Iterate over each tab pane detail and create elements
        tabPanes.forEach(pane => {
            let tabPane = document.createElement('div');
            tabPane.className = 'tab-pane fade' + (pane.id === 'agency-tab-pane' ? ' show active' : '');
            tabPane.id = pane.id + '_' + agency.agency_id;
            tabPane.setAttribute('role', 'tabpanel');
            tabPane.setAttribute('aria-labelledby', pane.id);
            tabPane.setAttribute('tabindex', '0');
            tabContentDiv.appendChild(tabPane);

            // Heading
            let heading = document.createElement('h5');
            heading.className = 'mt-3 mb-3';
            heading.textContent = pane.label;
            tabPane.appendChild(heading);

            // Fields
            pane.fields.forEach(field => {

                // Determine the value for this field from the current agency object
                let value = agency[field.id] || '';  // Use an empty string if the value isn't found

                // Special handling for 'alert_emails' field if it's an array
                if (field.id === 'alert_emails' && Array.isArray(value)) {
                    value = value.join(', ');  // Convert array to comma-separated string
                }

                let label = document.createElement('label');
                label.id = field.id + '_label_' + agency.agency_id;
                label.setAttribute('for', field.id + '_' + agency.agency_id);
                label.setAttribute('data-bs-toggle', 'tooltip');
                label.setAttribute('data-bs-placement', 'top');
                label.setAttribute('title', field.tooltip);
                label.className = 'form-label ' + field.class;
                label.textContent = field.label;
                tabPane.appendChild(label);

                // Create the input or textarea or select based on the type
                if (field.type === 'textarea') {
                    let textarea = document.createElement('textarea');
                    textarea.id = field.id + '_' + agency.agency_id;
                    textarea.name = field.id;
                    textarea.className = 'form-control mb-3 ' + field.class;
                    textarea.setAttribute('rows', '5');
                    textarea.setAttribute('cols', '50');
                    textarea.setAttribute('data-bs-toggle', 'tooltip');
                    textarea.setAttribute('data-bs-placement', 'top');
                    textarea.setAttribute('title', field.tooltip);
                    if (field.required) textarea.required = true;
                    textarea.textContent = value;  // Set the text content for a textarea
                    tabPane.appendChild(textarea);
                } else if (field.type === 'select') {
                    let select = document.createElement('select');
                    select.id = field.id + '_' + agency.agency_id;
                    select.name = field.id;
                    select.className = 'form-select mb-3 ' + field.class;
                    select.setAttribute('data-bs-toggle', 'tooltip');
                    select.setAttribute('data-bs-placement', 'top');
                    select.setAttribute('title', field.tooltip);
                    if (field.required) select.required = true;

                    // Add options to the select
                    field.options.forEach(option => {
                        let optionElement = document.createElement('option');
                        optionElement.value = option.value;
                        optionElement.textContent = option.text;
                        if (option.value === value) optionElement.selected = true;  // Set the current value
                        select.appendChild(optionElement);
                    });

                    tabPane.appendChild(select);
                } else {
                    let input = document.createElement('input');
                    input.setAttribute('type', field.type);
                    input.id = field.id + '_' + agency.agency_id;
                    input.name = field.id;
                    input.setAttribute('data-bs-toggle', 'tooltip');
                    input.setAttribute('data-bs-placement', 'top');
                    input.setAttribute('title', field.tooltip);
                    input.className = 'form-control mb-3 ' + field.class;
                    if (field.required) input.required = true;
                    input.value = value;  // Set the value for an input
                    tabPane.appendChild(input);
                }
            });
        });

        // Create the submit button
        let submitButton = document.createElement('button');
        submitButton.className = 'btn btn-success';
        submitButton.type = 'submit';
        submitButton.textContent = 'Save';

        // Add event listener to the form submission
        form.addEventListener('submit', function (event) {
            event.preventDefault(); // Prevent the default form submission

            // Get the form data
            let formData = new FormData(form);

            const fetchPromise = new Promise((resolve, reject) => {
                setTimeout(reject, 180000, new Error('Request timed out')); // Reject the promise after 180 seconds (3 minutes)
                fetch('/save_agency_config', {
                    method: 'POST',
                    body: formData
                })
                    .then(response => response.json())
                    .then(data => resolve(data))
                    .catch(error => reject(error));
            });

            fetchPromise
                .then(data => {
                    // Display success or error message
                    if (data.status === 'success') {
                        showAlert(alertDiv, data.message, 'alert-success');
                    } else {
                        showAlert(alertDiv, data.message, 'alert-danger');
                    }
                })
                .catch(error => {
                    showAlert(alertDiv, 'An error occurred: ' + error.message, 'alert-danger');
                });
        });

        // Append the submit button to the form
        form.appendChild(submitButton);

        // Append the form to the accordion body
        accordionBody.appendChild(form);

        // Append the accordion body to the accordion collapse container
        accordionCollapse.appendChild(accordionBody);

        // Append the accordion header and collapse to the accordion item
        accordionItem.appendChild(accordionHeader);
        accordionItem.appendChild(accordionCollapse);

        agencyConfig.appendChild(accordionItem);


    });

}

function toggleDisplayClass(element, shouldBeShown) {
    if (shouldBeShown){
        element.classList.remove('d-none');
    } else {
        element.classList.add('d-none');
    }

}

function showAlert(element, message, className) {

    // Reset any previous state
    element.textContent = '';
    element.classList.remove('alert-success', 'alert-danger');

    toggleDisplayClass(element, true);

    // Set new state
    element.textContent = message;
    element.classList.add(className);

    // Hide after 3 seconds
    setTimeout(() => {
        element.textContent = '';
        element.classList.remove(className);
        toggleDisplayClass(element, false);
    }, 3000);
}