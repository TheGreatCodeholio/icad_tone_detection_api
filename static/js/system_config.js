// System Select Div Elements
const systemSelect = document.getElementById('system_selection')

//System Form Elements Add/Update/Delete
const addSystemForm = document.getElementById('addSystemForm');
const addAgencyForm = document.getElementById('agency_input_form');
const deleteSystemForm = document.getElementById('deleteSystemForm')
const deleteAgencyForm = document.getElementById('deleteAgencyForm');

//System Button Elements Add/Update/Delete
const submitAddFormButton = document.getElementById('submitAddForm');
const submitAddAgencyButton = document.getElementById('submitAddAgencyForm')
const submitDeleteAgencyButton = document.getElementById('submitDeleteAgencyForm')
const submitDeleteButton = document.getElementById('submitDeleteForm')

//Alert Area
const alertDiv = document.getElementById('nav_alert');

// Load systems on page load
window.addEventListener('load', function () {
    const params = new URLSearchParams(window.location.search);
    const system_id = Number(params.get('system_id'));
    updateSystemSelection(system_id);
});

function generateUUIDv4() {
    return ([1e7] + -1e3 + -4e3 + -8e3 + -1e11).replace(/[018]/g, c =>
        (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
    );
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

    if (systemId === "") {
        const systemConfig = document.getElementById('accordionSystem');
        systemConfig.innerHTML = '';
        const agencyConfig = document.getElementById('accordionAgency');
        agencyConfig.innerHTML = '';
        return;
    }

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
    const systemConfig = document.getElementById('accordionSystem');
    systemConfig.innerHTML = '';
    const agencyConfig = document.getElementById('accordionAgency');
    agencyConfig.innerHTML = '';

    if (!system_data.length) return;

    const system = system_data[0];

    // Accordion item container
    const accordionItem = createElement('div', {className: 'accordion-item', parent: systemConfig});

    // Accordion header
    const accordionHeader = createElement('h2', {
        className: 'accordion-header',
        id: `heading_${system.system_id}`,
        parent: accordionItem
    });

    // Accordion button
    createElement('button', {
        className: 'accordion-button',
        attributes: {
            'data-bs-toggle': 'collapse',
            'data-bs-target': `#collapse_${system.system_id}`,
            'aria-expanded': 'false',
            'aria-controls': `collapse_${system.system_id}`
        },
        textContent: system.system_name,
        parent: accordionHeader,
        type: 'button'
    });

    // Accordion collapse container
    const accordionCollapse = createElement('div', {
        className: 'accordion-collapse collapse',
        id: `collapse_${system.system_id}`,
        attributes: {
            'aria-labelledby': `heading_${system.system_id}`,
            'data-bs-parent': '#accordionSystem'
        },
        parent: accordionItem
    });

    // Accordion body
    const accordionBody = createElement('div', {className: 'accordion-body', parent: accordionCollapse});

    //System Delete
    const sysDeleteButton = createElement('button', {
        parent: accordionBody,
        id: 'deleteSystemButton',
        className: 'btn btn-danger mb-3',
        attributes: {
            'data-bs-toggle': 'modal',
            'data-bs-target': '#deleteSystemModal',
            'data-system-id': system.system_id,
            'data-system-name': system.system_name,
            'data-system-short-name': system.system_short_name
        },
        innerHTML: 'Delete System'
    })

    const agencyAddButton = createElement('button', {
        parent: accordionBody,
        id: 'addAgencyButton',
        className: 'btn btn-primary mb-3 ms-2',
        attributes: {
            'data-bs-toggle': 'modal',
            'data-bs-target': '#addAgencyModal',
            'data-system-id': system.system_id
        },
        innerHTML: 'Add Agency'
    })

    // Form
    const form = createElement('form', {
        className: 'row g-3',
        id: `system_edit_form_${system.system_id}`,
        parent: accordionBody
    });

    // Dynamically create input fields based on system data
    const inputFields = [
        {
            label: 'System ID:',
            id: 'system_id',
            type: 'text',
            value: system.system_id,
            readOnly: true,
            tooltip: 'System Identifier'
        },
        {
            label: 'Short Name:',
            id: 'system_short_name',
            type: 'text',
            value: system.system_short_name,
            tooltip: 'Shorted System Name No Spaces'
        },
        {
            label: 'System Name:',
            id: 'system_name',
            type: 'text',
            value: system.system_name,
            tooltip: 'Name of the System'
        },
        {
            label: 'System County:',
            id: 'system_county',
            type: 'text',
            value: system.system_county,
            tooltip: 'County of the System'
        },
        {
            label: 'System State:',
            id: 'system_state',
            type: 'text',
            value: system.system_state,
            tooltip: 'State of the System'
        },
        {
            label: 'System FIPS:',
            id: 'system_fips',
            type: 'text',
            value: system.system_fips,
            tooltip: 'FIPS Code for the System'
        },
        {
            label: 'System API Key:',
            id: 'system_api_key',
            type: 'text',
            value: system.system_api_key,
            readOnly: true,
            tooltip: 'Your API Key',
            regenerate: true
        }
    ];

    inputFields.forEach(field => {
        if (field.regenerate) {
            // Handle API Key with regenerate button
            createFormField(form, field, system.system_id, field.value, true); // Assuming true indicates the presence of a regenerate button
        } else {
            // Regular input fields
            createFormField(form, field, system.system_id, field.value);
        }
    });

    const detailsAccordian = createElement('div', {id: "detailsAccordian", className: 'accordian', parent: form})

    // Accordion item container
    const accordionDetailsItem = createElement('div', {className: 'accordion-item', parent: detailsAccordian});

    // Accordion header
    const accordionDetailsHeader = createElement('h2', {
        className: 'accordion-header',
        id: `heading_details_${system.system_id}`,
        parent: accordionDetailsItem
    });

    // Accordion button
    createElement('button', {
        className: 'accordion-button',
        attributes: {
            'data-bs-toggle': 'collapse',
            'data-bs-target': `#collapse_details_${system.system_id}`,
            'aria-expanded': 'false',
            'aria-controls': `collapse_details_${system.system_id}`
        },
        textContent: `${system.system_name} Configuration`,
        parent: accordionDetailsHeader,
        type: 'button'
    });

    // Accordion collapse container
    const accordionDetailsCollapse = createElement('div', {
        className: 'accordion-collapse collapse',
        id: `collapse_details_${system.system_id}`,
        attributes: {
            'aria-labelledby': `heading_details_${system.system_id}`,
            'data-bs-parent': '#detailsAccordian'
        },
        parent: accordionDetailsItem
    });

    // Accordion body
    const accordionDetailsBody = createElement('div', {className: 'accordion-body', parent: accordionDetailsCollapse});

    // Dynamically create tabs and their content
    const tabsUl = createElement('ul', {
        className: 'nav nav-tabs',
        id: `system_tabs_${system.system_id}`,
        attributes: {'role': 'tablist'},
        parent: accordionDetailsBody // Assuming you want the tabs within the form, adjust if necessary
    });

    let tabNames = ['Emails', 'MQTT', 'Pushover', 'Facebook', 'Telegram', 'Streaming', 'Upload', 'Webhooks'];

    tabNames.forEach((tabName, index) => {
        const tabId = `${tabName.toLowerCase().replace(/\s+/g, '')}-tab_${system.system_id}`;
        const paneId = `${tabName.toLowerCase().replace(/\s+/g, '')}-tab-pane_${system.system_id}`;

        // Tab list item
        const li = createElement('li', {
            className: 'nav-item',
            attributes: {'role': 'presentation'},
            parent: tabsUl
        });

        // Tab button
        createElement('button', {
            className: `conf-link nav-link ${index === 0 ? 'active' : ''}`,
            id: tabId,
            attributes: {
                'data-bs-toggle': 'tab',
                'data-bs-target': `#${paneId}`,
                'type': 'button',
                'role': 'tab',
                'aria-controls': paneId,
                'aria-selected': index === 0 ? 'true' : 'false'
            },
            textContent: tabName,
            parent: li
        });
    });

    // Tab content container
    const tabContentDiv = createElement('div', {
        className: 'tab-content',
        id: `systemTabContent_${system.system_id}`,
        parent: accordionDetailsBody // Adjust the parent as needed
    });

    let tabPanes = [
        {
            id: 'emails-tab-pane',
            label: 'Alert Emails',
            fields: [
                {
                    label: 'Enable Emails',
                    id: 'email_enabled',
                    tooltip: 'Enable/Disable sending alerts via Email.',
                    type: 'select',
                    class: 'w-50',
                    options: [{value: '1', text: 'Enabled'}, {value: '0', text: 'Disabled', selected: true}]
                },
                {
                    label: 'SMTP Host',
                    id: 'smtp_hostname',
                    tooltip: 'Hostname for SMTP Server',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'SMTP Port',
                    id: 'smtp_port',
                    tooltip: 'SMTP Server Port',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'SMTP Username',
                    id: 'smtp_username',
                    tooltip: 'Username for SMTP Server',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'SMTP Password',
                    id: 'smtp_password',
                    tooltip: 'SMTP User\'s Password',
                    type: 'password',
                    class: 'w-50'
                },
                {
                    label: 'SMTP Server Security',
                    id: 'smtp_security',
                    tooltip: 'Security Type For SMTP TLS or SSL',
                    type: 'select',
                    class: 'w-50',
                    options: [{value: '1', text: 'SSL'}, {value: '2', text: 'TLS', selected: true}]
                },
                {
                    label: 'Email Address',
                    id: 'email_address_from',
                    tooltip: 'Email Address To Send Email From: icad@example.com',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'Email Name',
                    id: 'email_text_from',
                    tooltip: 'Name To Use When Sending Email: iCAD Dispatch',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'System Alert Email Addresses',
                    id: 'system_alert_emails',
                    tooltip: 'Comma separated list of subscribed email addresses.',
                    type: 'textarea',
                    class: 'w-100'
                },
                {
                    label: 'Alert Email Subject',
                    id: 'email_alert_subject',
                    tooltip: 'Alert Email Subject',
                    type: 'text',
                    class: 'w-100'
                },
                {
                    label: 'Alert Email Body',
                    id: 'email_alert_body',
                    tooltip: 'Alert Email Body',
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
                    label: 'Enable MQTT',
                    id: 'mqtt_enabled',
                    tooltip: 'Enable/Disable sending alerts via MQTT.',
                    type: 'select',
                    class: 'w-50',
                    options: [{value: '1', text: 'Enabled'}, {value: '0', text: 'Disabled', selected: true}]
                },
                {
                    label: 'MQTT Host',
                    id: 'mqtt_hostname',
                    tooltip: 'MQTT Hostname.',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'MQTT Port',
                    id: 'mqtt_port',
                    tooltip: 'MQTT Port.',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'MQTT Username',
                    id: 'mqtt_username',
                    tooltip: 'MQTT Username.',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'MQTT Password',
                    id: 'mqtt_password',
                    tooltip: 'MQTT Password.',
                    type: 'password',
                    class: 'w-50'
                }
            ]
        },
        {
            id: 'pushover-tab-pane',
            label: 'Pushover Configuration',
            fields: [
                {
                    label: 'Enable Pushover',
                    id: 'pushover_enabled',
                    tooltip: 'Enable/Disable sending alerts via Pushover.',
                    type: 'select',
                    class: 'w-50',
                    options: [{value: '1', text: 'Enabled'}, {value: '0', text: 'Disabled', selected: true}]
                },
                {
                    label: 'All Agency Group Token',
                    id: 'pushover_all_group_token',
                    tooltip: 'Group token from Pushover For All Agencies.',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'All Agency App Token',
                    id: 'pushover_all_app_token',
                    tooltip: 'App Token from Pushover App for All Agencies.',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'Pushover Message Subject',
                    id: 'pushover_subject',
                    tooltip: 'Subject for Pushover Message.',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'Pushover Message HTML',
                    id: 'pushover_body',
                    tooltip: 'Message Body for Pushover.',
                    type: 'textarea',
                    class: 'w-50'
                },
                {
                    label: 'Pushover Alert Sound',
                    id: 'pushover_sound',
                    tooltip: 'Alert Sound for Pushover Notification.',
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
                    label: 'Enable Facebook Posting',
                    id: 'facebook_enabled',
                    tooltip: 'Enable/Disable posting to Facebook.',
                    type: 'select',
                    class: 'w-50',
                    options: [{value: '1', text: 'Enabled'}, {value: '0', text: 'Disabled', selected: true}]
                },
                {
                    label: 'Facebook Page ID',
                    id: 'facebook_page_id',
                    tooltip: 'Facebook Page ID.',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'Facebook Page Token',
                    id: 'facebook_page_token',
                    tooltip: 'Facebook Page Token',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'Facebook Group ID',
                    id: 'facebook_group_id',
                    tooltip: 'Facebook Group ID.',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'Facebook Group Token',
                    id: 'facebook_group_token',
                    tooltip: 'Facebook Group Token',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'Facebook Post Body',
                    id: 'facebook_post_body',
                    tooltip: 'Post Body For Facebook.',
                    type: 'textarea',
                    class: 'w-50'
                },
                {
                    label: 'Post Comment',
                    id: 'facebook_comment_enabled',
                    tooltip: 'Post Comment to Post With Additional Information.',
                    type: 'select',
                    class: 'w-50',
                    options: [{value: '1', text: 'Enabled'}, {value: '0', text: 'Disabled', selected: true}]
                },
                {
                    label: 'Facebook Comment Message',
                    id: 'facebook_comment_body',
                    tooltip: 'Post Comment Body',
                    type: 'textarea',
                    class: 'w-50'
                }
            ]
        },
        {
            id: 'telegram-tab-pane',
            label: 'Telegram Configuration',
            fields: [
                {
                    label: 'Enable Telegram Channel Posting',
                    id: 'telegram_enabled',
                    tooltip: 'Enable/Disable posting to Telegram.',
                    type: 'select',
                    class: 'w-50',
                    options: [{value: '1', text: 'Enabled'}, {value: '0', text: 'Disabled', selected: true}]
                },
                {
                    label: 'Telegram Channel ID',
                    id: 'telegram_channel_id',
                    tooltip: 'Telegram Channel ID.',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'Telegram Bot Token',
                    id: 'telegram_bot_token',
                    tooltip: 'Telegram Bot Token issued by Bot Father',
                    type: 'text',
                    class: 'w-50'
                }
            ]
        },
        {
            id: 'streaming-tab-pane',
            label: 'Streaming Configuration',
            fields: [
                {
                    label: 'Stream URL',
                    id: 'stream_url',
                    tooltip: 'URL Users Can Access Audio Stream: Icecast, RDIO, Broadcastify, OpenMHZ',
                    type: 'text',
                    class: 'w-50'
                },

            ]
        },
        {
            id: 'upload-tab-pane',
            label: 'SCP Configuration',
            fields: [
                {
                    label: 'Enable SCP File Storage',
                    id: 'scp_enabled',
                    tooltip: 'Enable/Disable SCP File Storage',
                    type: 'select',
                    class: 'w-50',
                    options: [{value: '1', text: 'Enabled'}, {value: '0', text: 'Disabled', selected: true}]
                },
                {
                    label: 'SCP Host',
                    id: 'scp_host',
                    tooltip: 'Hostname for SCP Server',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'SCP Port',
                    id: 'scp_port',
                    tooltip: 'SCP Server Port',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'SCP Username',
                    id: 'scp_username',
                    tooltip: 'Username for SCP Server',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'SCP Password',
                    id: 'scp_password',
                    tooltip: 'SCP User\'s Password',
                    type: 'password',
                    class: 'w-50'
                },
                {
                    label: 'SCP Private Key',
                    id: 'scp_private_key',
                    tooltip: 'SCP User\'s Private Key. Leave empty to use password auth.',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'SCP Remote Folder',
                    id: 'scp_remote_folder',
                    tooltip: 'SCP Remote Folder Path.',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'SCP Audio URL Path',
                    id: 'web_url_path',
                    tooltip: 'URL For Audio Path: https://example.com/detection_audio',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'SCP Archive',
                    id: 'scp_archive_days',
                    tooltip: 'Number of Days to Keep Uploaded Audio: 0 Keeps forever.',
                    type: 'text',
                    class: 'w-50'
                }
            ]
        },
        {
            id: 'webhooks-tab-pane',
            label: 'Webhooks Configuration',
            fields: [
                {
                    label: ' Enable Webhook',
                    id: 'webhook_enabled',
                    tooltip: 'Enable/Disable Posting Webhook',
                    type: 'select',
                    class: 'w-50',
                    options: [{value: '1', text: 'Enabled'}, {value: '0', text: 'Disabled', selected: true}]
                },
                {
                    label: 'Webhook URL',
                    id: 'webhook_url',
                    tooltip: 'URL to Make Webhook Post To.',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'Webhook Headers',
                    id: 'webhook_headers',
                    tooltip: 'Header to Send with the Webhook Post: JSON Format',
                    type: 'textarea',
                    class: 'w-100'
                }

            ]
        }
    ];

    // Dynamically create content for each tab
    tabPanes.forEach(pane => {
        const paneId = `${pane.id}_${system.system_id}`;
        const tabPane = createElement('div', {
            className: `tab-pane fade ${pane.id === 'emails-tab-pane' ? 'show active' : ''}`,
            id: paneId,
            attributes: {
                'role': 'tabpanel',
                'aria-labelledby': pane.id
            },
            parent: tabContentDiv
        });

        // Heading for each tab pane
        createElement('h5', {
            className: 'mt-3 mb-3',
            textContent: pane.label,
            parent: tabPane
        });

        const tabPaneDiv = createElement('div', {
            className: 'row g-3',
            id: `system_details_form_${system.system_id}`,
            parent: tabPane
        });

        // Fields for each tab pane
        pane.fields.forEach(field => {
            const fieldValue = system[field.id];
            createFormField(tabPaneDiv, field, system.system_id, fieldValue)
        });
    });

    // Submit button
    createElement('button', {
        className: 'btn btn-success',
        type: 'submit',
        textContent: 'Save',
        parent: form
    });

    // Form submission event
    form.addEventListener('submit', function (event) {
        event.preventDefault();
        handleSystemFormSubmit(system.system_id, form);
    });

    // Assuming showAgencies function is defined and works with the refactored system data
    showAgencies(system);
}

function showSystem_old(system_data) {
    let systemConfig = document.getElementById('accordionSystem');
    systemConfig.innerHTML = ''

    if (system_data.length < 1) {
        return;
    }
    system_data = system_data[0]

    // Populate Delete Modal
    const system_delete = document.getElementById('deleteSystemId')
    const system_name_delete = document.getElementById('deleteSystemName')
    const del_system_title = document.getElementById('deletesystemNameTitle')

    system_delete.value = system_data.system_id;
    system_name_delete.value = system_data.system_short_name;
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
    agencyAddButton.setAttribute("class", "btn btn-primary mb-3 ms-2");
    agencyAddButton.setAttribute("data-bs-toggle", "modal");
    agencyAddButton.setAttribute("data-bs-target", "#addAgencyModal");
    agencyAddButton.setAttribute("data-system-id", system_data.system_id);
    agencyAddButton.innerHTML = "Add Agency";
    accordionBody.appendChild(agencyAddButton);

    // Create the form
    let form = document.createElement('form');
    form.className = 'row g-3';
    form.id = 'system_edit_form_' + system_data.system_id

    // Create the system id text input
    let systemIdLabel = document.createElement('label');
    systemIdLabel.className = 'col-md-6 form-label';
    systemIdLabel.textContent = 'System ID:';
    let systemIdInput = document.createElement('input');
    systemIdInput.className = 'col-md-6 form-control';
    systemIdInput.type = 'text';
    systemIdInput.name = 'system_id';
    systemIdInput.readOnly = true;
    systemIdInput.value = system_data.system_id;
    systemIdLabel.appendChild(systemIdInput);
    form.appendChild(systemIdLabel);

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
    systemFIPSLabel.textContent = 'System FIPS:';
    let systemFIPSInput = document.createElement('input');
    systemFIPSInput.className = 'col-md-6 form-control';
    systemFIPSInput.type = 'text';
    systemFIPSInput.name = 'system_fips';
    systemFIPSInput.value = system_data.system_fips;
    systemFIPSLabel.appendChild(systemFIPSInput);
    form.appendChild(systemFIPSLabel);

    // Create the wrapper div
    let systemAPIWrapper = document.createElement('div');
    systemAPIWrapper.className = 'input-group mb-3';

    // Create the system API key input
    let systemAPIInput = document.createElement('input');
    systemAPIInput.className = 'form-control';
    systemAPIInput.type = 'text';
    systemAPIInput.name = 'system_api_key';
    systemAPIInput.readOnly = true;
    systemAPIInput.value = system_data.system_api_key; // Assuming system_data.system_api_key exists

    // Create the regenerate icon button
    let regenerateBtn = document.createElement('button');
    regenerateBtn.className = 'btn btn-outline-secondary';
    regenerateBtn.type = 'button';
    regenerateBtn.innerHTML = '<i class="fas fa-sync-alt"></i>'; // Font Awesome sync-alt icon
    regenerateBtn.onclick = function () {
        systemAPIInput.value = generateUUIDv4(); // Generate a new UUIDv4 and set it as the input's value
    };

    // Append the API input and regenerate button to the wrapper
    systemAPIWrapper.appendChild(systemAPIInput);
    systemAPIWrapper.appendChild(regenerateBtn);

    // Append the wrapper to the form
    form.appendChild(systemAPIWrapper);

    // Create the main div container
    let systemInputDiv = document.createElement('div');
    systemInputDiv.id = 'system_input_div_' + system_data.system_id;
    form.appendChild(systemInputDiv);

    // Create the ul element for tabs
    let tabsUl = document.createElement('ul');
    tabsUl.className = 'nav nav-tabs';
    tabsUl.id = 'system_tabs_' + system_data.system_id;
    tabsUl.setAttribute('role', 'tablist');
    systemInputDiv.appendChild(tabsUl);

    // Array of tab names
    let tabNames = ['Emails', 'MQTT', 'Pushover', 'Facebook', 'Telegram', 'Streaming', 'Upload', 'Webhooks'];

    tabNames.forEach((tabName, index) => {
        let li = document.createElement('li');
        li.className = 'nav-item';
        li.setAttribute('role', 'presentation');

        let button = document.createElement('button');
        button.className = 'conf-link nav-link' + (index === 0 ? ' active' : '');
        button.id = tabName.toLowerCase().replace(/\s+/g, '') + '-tab_' + system_data.system_id;
        button.setAttribute('data-bs-toggle', 'tab');
        button.setAttribute('data-bs-target', '#' + tabName.toLowerCase().replace(/\s+/g, '') + '-tab-pane_' + system_data.system_id);
        button.setAttribute('type', 'button');
        button.setAttribute('role', 'tab');
        button.setAttribute('aria-controls', tabName.toLowerCase().replace(/\s+/g, '') + '-tab-pane_' + system_data.system_id);
        button.setAttribute('aria-selected', index === 0 ? 'true' : 'false');
        button.textContent = tabName;

        li.appendChild(button);
        tabsUl.appendChild(li);
    });

    // Create the tab-content div
    let tabContentDiv = document.createElement('div');
    tabContentDiv.className = 'tab-content';
    tabContentDiv.id = 'agencyTabContent_' + system_data.system_id;
    systemInputDiv.appendChild(tabContentDiv);

    let tabPanes = [
        {
            id: 'emails-tab-pane',
            label: 'Alert Emails',
            fields: [
                {
                    label: 'Enable Emails',
                    id: 'email_enabled',
                    tooltip: 'Enable/Disable sending alerts via Email.',
                    type: 'select',
                    class: 'w-50',
                    options: [{value: '1', text: 'Enabled'}, {value: '0', text: 'Disabled', selected: true}]
                },
                {
                    label: 'SMTP Host',
                    id: 'smtp_hostname',
                    tooltip: 'Hostname for SMTP Server',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'SMTP Port',
                    id: 'smtp_port',
                    tooltip: 'SMTP Server Port',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'SMTP Username',
                    id: 'smtp_username',
                    tooltip: 'Username for SMTP Server',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'SMTP Password',
                    id: 'smtp_password',
                    tooltip: 'SMTP User\'s Password',
                    type: 'password',
                    class: 'w-50'
                },
                {
                    label: 'SMTP Server Security',
                    id: 'smtp_security',
                    tooltip: 'Security Type For SMTP TLS or SSL',
                    type: 'select',
                    class: 'w-50',
                    options: [{value: '1', text: 'SSL'}, {value: '2', text: 'TLS', selected: true}]
                },
                {
                    label: 'Email Address',
                    id: 'email_address_from',
                    tooltip: 'Email Address To Send Email From: icad@example.com',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'Email Name',
                    id: 'email_text_from',
                    tooltip: 'Name To Use When Sending Email: iCAD Dispatch',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'System Alert Email Addresses',
                    id: 'system_alert_emails',
                    tooltip: 'Comma separated list of subscribed email addresses.',
                    type: 'textarea',
                    class: 'w-100'
                },
                {
                    label: 'Alert Email Subject',
                    id: 'email_alert_subject',
                    tooltip: 'Alert Email Subject',
                    type: 'text',
                    class: 'w-100'
                },
                {
                    label: 'Alert Email Body',
                    id: 'email_alert_body',
                    tooltip: 'Alert Email Body',
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
                    label: 'Enable MQTT',
                    id: 'mqtt_enabled',
                    tooltip: 'Enable/Disable sending alerts via MQTT.',
                    type: 'select',
                    class: 'w-50',
                    options: [{value: '1', text: 'Enabled'}, {value: '0', text: 'Disabled', selected: true}]
                },
                {
                    label: 'MQTT Host',
                    id: 'mqtt_hostname',
                    tooltip: 'MQTT Hostname.',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'MQTT Port',
                    id: 'mqtt_port',
                    tooltip: 'MQTT Port.',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'MQTT Username',
                    id: 'mqtt_username',
                    tooltip: 'MQTT Username.',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'MQTT Password',
                    id: 'mqtt_password',
                    tooltip: 'MQTT Password.',
                    type: 'password',
                    class: 'w-50'
                }
            ]
        },
        {
            id: 'pushover-tab-pane',
            label: 'Pushover Configuration',
            fields: [
                {
                    label: 'Enable Pushover',
                    id: 'pushover_enabled',
                    tooltip: 'Enable/Disable sending alerts via Pushover.',
                    type: 'select',
                    class: 'w-50',
                    options: [{value: '1', text: 'Enabled'}, {value: '0', text: 'Disabled', selected: true}]
                },
                {
                    label: 'All Agency Group Token',
                    id: 'pushover_all_group_token',
                    tooltip: 'Group token from Pushover For All Agencies.',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'All Agency App Token',
                    id: 'pushover_all_app_token',
                    tooltip: 'App Token from Pushover App for All Agencies.',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'Pushover Message Subject',
                    id: 'pushover_subject',
                    tooltip: 'Subject for Pushover Message.',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'Pushover Message HTML',
                    id: 'pushover_body',
                    tooltip: 'Message Body for Pushover.',
                    type: 'textarea',
                    class: 'w-50'
                },
                {
                    label: 'Pushover Alert Sound',
                    id: 'pushover_sound',
                    tooltip: 'Alert Sound for Pushover Notification.',
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
                    label: 'Enable Facebook Posting',
                    id: 'facebook_enabled',
                    tooltip: 'Enable/Disable posting to Facebook.',
                    type: 'select',
                    class: 'w-50',
                    options: [{value: '1', text: 'Enabled'}, {value: '0', text: 'Disabled', selected: true}]
                },
                {
                    label: 'Facebook Page ID',
                    id: 'facebook_page_id',
                    tooltip: 'Facebook Page ID.',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'Facebook Page Token',
                    id: 'facebook_page_token',
                    tooltip: 'Facebook Page Token',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'Facebook Group ID',
                    id: 'facebook_group_id',
                    tooltip: 'Facebook Group ID.',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'Facebook Group Token',
                    id: 'facebook_group_token',
                    tooltip: 'Facebook Group Token',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'Facebook Post Body',
                    id: 'facebook_post_body',
                    tooltip: 'Post Body For Facebook.',
                    type: 'textarea',
                    class: 'w-50'
                },
                {
                    label: 'Post Comment',
                    id: 'facebook_comment_enabled',
                    tooltip: 'Post Comment to Post With Additional Information.',
                    type: 'select',
                    class: 'w-50',
                    options: [{value: '1', text: 'Enabled'}, {value: '0', text: 'Disabled', selected: true}]
                },
                {
                    label: 'Facebook Comment Message',
                    id: 'facebook_comment_body',
                    tooltip: 'Post Comment Body',
                    type: 'textarea',
                    class: 'w-50'
                }
            ]
        },
        {
            id: 'telegram-tab-pane',
            label: 'Telegram Configuration',
            fields: [
                {
                    label: 'Enable Telegram Channel Posting',
                    id: 'telegram_enabled',
                    tooltip: 'Enable/Disable posting to Telegram.',
                    type: 'select',
                    class: 'w-50',
                    options: [{value: '1', text: 'Enabled'}, {value: '0', text: 'Disabled', selected: true}]
                },
                {
                    label: 'Telegram Channel ID',
                    id: 'telegram_channel_id',
                    tooltip: 'Telegram Channel ID.',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'Telegram Bot Token',
                    id: 'telegram_bot_token',
                    tooltip: 'Telegram Bot Token issued by Bot Father',
                    type: 'text',
                    class: 'w-50'
                }
            ]
        },
        {
            id: 'streaming-tab-pane',
            label: 'Streaming Configuration',
            fields: [
                {
                    label: 'Stream URL',
                    id: 'stream_url',
                    tooltip: 'URL Users Can Access Audio Stream: Icecast, RDIO, Broadcastify, OpenMHZ',
                    type: 'text',
                    class: 'w-50'
                },

            ]
        },
        {
            id: 'upload-tab-pane',
            label: 'SCP Configuration',
            fields: [
                {
                    label: 'Enable SCP File Storage',
                    id: 'scp_enabled',
                    tooltip: 'Enable/Disable SCP File Storage',
                    type: 'select',
                    class: 'w-50',
                    options: [{value: '1', text: 'Enabled'}, {value: '0', text: 'Disabled', selected: true}]
                },
                {
                    label: 'SCP Host',
                    id: 'scp_host',
                    tooltip: 'Hostname for SCP Server',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'SCP Port',
                    id: 'scp_port',
                    tooltip: 'SCP Server Port',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'SCP Username',
                    id: 'scp_username',
                    tooltip: 'Username for SCP Server',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'SCP Password',
                    id: 'scp_password',
                    tooltip: 'SCP User\'s Password',
                    type: 'password',
                    class: 'w-50'
                },
                {
                    label: 'SCP Private Key',
                    id: 'scp_private_key',
                    tooltip: 'SCP User\'s Private Key. Leave empty to use password auth.',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'SCP Remote Folder',
                    id: 'scp_remote_folder',
                    tooltip: 'SCP Remote Folder Path.',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'SCP Audio URL Path',
                    id: 'web_url_path',
                    tooltip: 'URL For Audio Path: https://example.com/detection_audio',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'SCP Archive',
                    id: 'scp_archive_days',
                    tooltip: 'Number of Days to Keep Uploaded Audio: 0 Keeps forever.',
                    type: 'text',
                    class: 'w-50'
                }
            ]
        },
        {
            id: 'webhooks-tab-pane',
            label: 'Webhooks Configuration',
            fields: [
                {
                    label: ' Enable Webhook',
                    id: 'webhook_enabled',
                    tooltip: 'Enable/Disable Posting Webhook',
                    type: 'select',
                    class: 'w-50',
                    options: [{value: '1', text: 'Enabled'}, {value: '0', text: 'Disabled', selected: true}]
                },
                {
                    label: 'Webhook URL',
                    id: 'webhook_url',
                    tooltip: 'URL to Make Webhook Post To.',
                    type: 'text',
                    class: 'w-50'
                },
                {
                    label: 'Webhook Headers',
                    id: 'webhook_headers',
                    tooltip: 'Header to Send with the Webhook Post: JSON Format',
                    type: 'textarea',
                    class: 'w-100'
                }

            ]
        }
    ];

    // Iterate over each tab pane detail and create elements
    tabPanes.forEach(pane => {
        let tabPane = document.createElement('div');
        tabPane.className = 'tab-pane fade' + (pane.id === 'emails-tab-pane' ? ' show active' : '');
        tabPane.id = pane.id + '_' + system_data.system_id;
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

            // Determine the value for this field from the current system object
            let value = system_data[field.id] !== undefined && system_data[field.id] !== null ? system_data[field.id] : '';

            // Special handling for 'alert_emails' field if it's an array
            if (field.id === 'system_alert_emails' && Array.isArray(value)) {
                value = value.join(', ');  // Convert array to comma-separated string
            }

            let label = document.createElement('label');
            label.id = field.id + '_label_' + system_data.system_id;
            label.setAttribute('for', field.id + '_' + system_data.system_id);
            label.setAttribute('data-bs-toggle', 'tooltip');
            label.setAttribute('data-bs-placement', 'top');
            label.setAttribute('title', field.tooltip);
            label.className = 'form-label ' + field.class;
            label.textContent = field.label;
            tabPane.appendChild(label);

            // Create the input or textarea or select based on the type
            if (field.type === 'textarea') {
                let textarea = document.createElement('textarea');
                textarea.id = field.id + '_' + system_data.system_id;
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
                select.id = field.id + '_' + system_data.system_id;
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
                    if (option.value === value.toString()) optionElement.selected = true;  // Set the current value
                    select.appendChild(optionElement);
                });

                tabPane.appendChild(select);
            } else {
                // Create a div to wrap input and icon
                let wrapperDiv = document.createElement('div');
                wrapperDiv.className = 'input-group mb-3';

                let input = document.createElement('input');
                input.setAttribute('type', field.type);
                input.id = field.id + '_' + system_data.system_id;
                input.name = field.id;
                input.setAttribute('data-bs-toggle', 'tooltip');
                input.setAttribute('data-bs-placement', 'top');
                input.setAttribute('title', field.tooltip);
                input.className = 'form-control ' + field.class;
                if (field.required) input.required = true;
                input.value = value;  // Set the value for an input

                wrapperDiv.appendChild(input);

                // Check if the field type is password to add the eyeball icon
                if (field.type === 'password') {
                    let toggleVisibilityBtn = document.createElement('button');
                    toggleVisibilityBtn.type = 'button';
                    toggleVisibilityBtn.className = 'btn btn-outline-secondary';
                    toggleVisibilityBtn.innerHTML = '<i class="fa-regular fa-eye"></i>'; // Font Awesome Icons eye for showing password
                    toggleVisibilityBtn.onclick = function () {
                        if (input.type === 'password') {
                            input.type = 'text';
                            toggleVisibilityBtn.innerHTML = '<i class="fa-solid fa-eye-slash"></i>'; // Change to eye-slash icon
                        } else {
                            input.type = 'password';
                            toggleVisibilityBtn.innerHTML = '<i class="fa-regular fa-eye"></i>'; // Change back to eye icon
                        }
                    };

                    let appendAddon = document.createElement('div');
                    appendAddon.className = 'input-group-append';
                    appendAddon.appendChild(toggleVisibilityBtn);

                    wrapperDiv.appendChild(appendAddon);
                }

                tabPane.appendChild(wrapperDiv);
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
            fetch('/admin/save_system', {
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
                if (data.success) {
                    updateSystemSelection(system_data.system_id)
                    showAlert(data.message, 'success');
                } else {
                    updateSystemSelection(system_data.system_id)
                    showAlert(data.message, 'danger');
                }
            })
            .catch(error => {
                showAlert('An error occurred: ' + error.message, 'danger');
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
        accordionHeader.id = 'heading_agency_' + agency.agency_id;

        // Create the accordion button
        let accordionButton = document.createElement('button');
        accordionButton.className = 'accordion-button';
        accordionButton.type = 'button';
        accordionButton.setAttribute('data-bs-toggle', 'collapse');
        accordionButton.setAttribute('data-bs-target', '#collapse_agency_' + agency.agency_id);
        accordionButton.setAttribute('aria-expanded', 'false');
        accordionButton.setAttribute('aria-controls', 'collapse_agency_' + agency.agency_id);
        accordionButton.textContent = agency.agency_name;

        // Append the accordion button to the accordion header
        accordionHeader.appendChild(accordionButton);

        // Create the accordion collapse container
        let accordionCollapse = document.createElement('div');
        accordionCollapse.id = 'collapse_agency_' + agency.agency_id;
        accordionCollapse.className = 'accordion-collapse collapse';
        accordionCollapse.setAttribute('aria-labelledby', 'heading_agency_' + agency.agency_id);
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

        // Hidden input for agency_id
        let hiddenInputAgencyId = document.createElement('input');
        hiddenInputAgencyId.setAttribute('type', 'hidden');
        hiddenInputAgencyId.className = 'form-control';
        hiddenInputAgencyId.id = 'addAgencyAgencyId_' + agency.agency_id;
        hiddenInputAgencyId.name = 'agency_id';
        hiddenInputAgencyId.value = agency.agency_id
        form.appendChild(hiddenInputAgencyId);

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
        let tabNames = ['Agency', 'QCII Tones', 'Email', 'MQTT', 'Pushover', 'Webhook', 'Facebook', 'Telegram'];

        // Create li and button elements for each tab
        tabNames.forEach((tabName, index) => {
            let li = document.createElement('li');
            li.className = 'nav-item';
            li.setAttribute('role', 'presentation');

            let button = document.createElement('button');
            button.className = 'conf-link nav-link' + (index === 0 ? ' active' : '');
            button.id = tabName.toLowerCase().replace(/\s+/g, '') + '-tab_agency_' + agency.agency_id;
            button.setAttribute('data-bs-toggle', 'tab');
            button.setAttribute('data-bs-target', '#' + tabName.toLowerCase().replace(/\s+/g, '') + '-tab-pane_agency_' + agency.agency_id);
            button.setAttribute('type', 'button');
            button.setAttribute('role', 'tab');
            button.setAttribute('aria-controls', tabName.toLowerCase().replace(/\s+/g, '') + '-tab-pane_agency_' + agency.agency_id);
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
                        class: 'w-75'
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
                        class: 'w-75'
                    },
                    {
                        label: 'Tone B Frequency',
                        id: 'b_tone',
                        tooltip: 'Quick Call II Tone B',
                        type: 'text',
                        class: 'w-75'
                    },
                    {
                        label: 'Tone C Frequency',
                        id: 'c_tone',
                        tooltip: 'Quick Call II Tone C',
                        type: 'text',
                        class: 'w-75'
                    },
                    {
                        label: 'Tone D Frequency',
                        id: 'd_tone',
                        tooltip: 'Quick Call II Tone D',
                        type: 'text',
                        class: 'w-75'
                    },
                    {
                        label: 'Tone Match Tolerance',
                        id: 'tone_tolerance',
                        tooltip: 'plus/minus tolerance in decimal form applied to a frequency to determine a match. 0.05 is 5%',
                        type: 'text',
                        class: 'w-50'
                    },
                    {
                        label: 'Agency Ignore Time',
                        id: 'ignore_time',
                        tooltip: 'Ignore time in seconds after a successful match.',
                        type: 'text',
                        class: 'w-75'
                    }
                ]
            },
            {
                id: 'email-tab-pane',
                label: 'Alert Emails',
                fields: [
                    {
                        label: 'Subscriber Email Addresses',
                        id: 'alert_emails',
                        tooltip: 'Comma separated list of Email addresses.',
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
                        label: 'Agency Pushover Message Subject',
                        id: 'pushover_subject',
                        tooltip: 'Agency Alert Subject for Pushover Message.',
                        type: 'text',
                        class: 'w-50'
                    },
                    {
                        label: 'Agency Pushover Message HTML',
                        id: 'pushover_body',
                        tooltip: 'Agency Alert Message Body for Pushover.',
                        type: 'textarea',
                        class: 'w-50'
                    },
                    {
                        label: 'Pushover Alert Sound',
                        id: 'pushover_sound',
                        tooltip: 'Agency Alert Sound for Pushover Notification.',
                        type: 'text',
                        class: 'w-50'
                    }
                ]
            },
            {
                id: 'webhook-tab-pane',
                label: 'Webhook Configuration',
                fields: [
                    {
                        label: 'Webhook URL',
                        id: 'webhook_url',
                        tooltip: 'Group token from Pushover group for this agency.',
                        type: 'text',
                        class: 'w-50'
                    },
                    {
                        label: 'Webhook Headers',
                        id: 'webhook_headers',
                        tooltip: 'JSON Array of Headers',
                        type: 'textarea',
                        class: 'w-100'
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
                        tooltip: 'Post Agency Alerts To Facebook.',
                        type: 'select',
                        class: 'w-50',
                        options: [{value: '1', text: 'Enabled'}, {value: '0', text: 'Disabled'}]
                    }
                ]
            },
            {
                id: 'telegram-tab-pane',
                label: 'Telegram Configuration',
                fields: [
                    {
                        label: 'Posting to Telegram',
                        id: 'enable_telegram_post',
                        tooltip: 'Post Agency Alerts To Telegram.',
                        type: 'select',
                        class: 'w-50',
                        options: [{value: '1', text: 'Enabled'}, {value: '0', text: 'Disabled'}]
                    }
                ]
            }
        ];

        // Iterate over each tab pane detail and create elements
        tabPanes.forEach(pane => {
            let tabPane = document.createElement('div');
            tabPane.className = 'tab-pane fade' + (pane.id === 'agency-tab-pane' ? ' show active' : '');
            tabPane.id = pane.id + '_agency_' + agency.agency_id;
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

                        let fieldValue = isNaN(parseInt(value)) ? value : parseInt(value);
                        let optionValue = isNaN(parseInt(option.value)) ? option.value : parseInt(option.value);

                        if (fieldValue == optionValue) {
                            optionElement.selected = true;
                        }

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
        submitButton.id = "agency_submit_" + agency.agency_id
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
                fetch('/admin/save_agency', {
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
                    if (data.success === true) {
                        showAlert(data.message, 'success');
                    } else {
                        showAlert(data.message, 'danger');
                    }
                })
                .catch(error => {
                    showAlert('An error occurred: ' + error.message, 'danger');
                });


        });

        // Append the submit button to the form
        form.appendChild(submitButton);

        // add delete button to the form
        const agencyDeleteButton = createElement('button', {
            parent: form,
            id: 'deleteAgencyButton',
            className: 'btn btn-danger mb-3 ms-2',
            attributes: {
                'data-bs-toggle': 'modal',
                'data-bs-target': '#deleteAgencyModal',
                'data-system-id': system_data.system_id,
                'data-agency-id': agency.agency_id,
                'data-agency-name': agency.agency_name
            },
            type: 'button',
            innerHTML: 'Delete Agency'
        })

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
    if (shouldBeShown) {
        element.classList.remove('d-none');
    } else {
        element.classList.add('d-none');
    }

}

function toggleModal(element) {
    const modal = new bootstrap.Modal(element);
    const body = document.body;
    const modalBackdrop = document.querySelector('.modal-backdrop');
    const footer = document.querySelector('footer');
    const navbar = document.querySelector('nav.navbar');

    // Check if the modal is currently displayed
    if (element.classList.contains('show')) {
        modal.hide();
        // Modal is displayed, so hide it
        element.classList.remove('show');
        element.style.display = 'none';
        element.removeAttribute('aria-modal');

        // Adjust the body style and class
        body.style.overflow = '';
        body.style.paddingRight = '';
        body.classList.remove('modal-open');

        // Adjust the footer and navbar style
        footer.style.paddingRight = '';
        navbar.style.paddingRight = '';

        // Remove modal-backdrop if it exists
        if (modalBackdrop) {
            modalBackdrop.remove();
        }

    } else {
        modal.show();
        // Modal is hidden, so display it
        element.classList.add('show');
        element.style.display = 'block';
        element.setAttribute('aria-modal', 'true');

        // Adjust the body style and class
        body.style.overflow = 'hidden';
        body.style.paddingRight = '0px';
        body.classList.add('modal-open');

        // Adjust the footer and navbar style
        footer.style.paddingRight = '0px';
        navbar.style.paddingRight = '0px';

        // Create modal-backdrop if it doesn't exist
        if (!modalBackdrop) {
            const backdropDiv = document.createElement('div');
            backdropDiv.classList.add('modal-backdrop', 'fade', 'show');
            body.appendChild(backdropDiv);
        }
    }
}

function handleSystemFormSubmit(systemId, form) {
    const formData = new FormData(form);
    formData.append('system_id', systemId); // Ensure system ID is included if not already part of the form

    fetch('/admin/save_system', {
        method: 'POST',
        body: formData
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateSystemSelection(systemId)
                showAlert(data.message, 'success');
            } else {
                updateSystemSelection(systemId)
                showAlert(data.message, 'danger');
            }
        })
        .catch(error => {
            console.error('Error updating system:', error);
            showAlert('An error occurred: ' + error.message, 'danger');
        });
}

submitAddFormButton.addEventListener('click', function () {

    const formData = new FormData(addSystemForm);
    const addSystemModal = document.getElementById('addSystemModal')

    toggleDisplayClass(addSystemForm, false)

    const loadingElement = document.getElementById('addloadingIndicator');
    toggleDisplayClass(loadingElement, true)

    const params = new URLSearchParams({
        new_system: true
    });

    const fetchPromise = new Promise((resolve, reject) => {
        setTimeout(reject, 180000, new Error('Request timed out'));
        fetch('/admin/save_system?' + params.toString(), {
            method: 'POST',
            body: formData
        })
            .then(response => response.json())
            .then(data => resolve(data))
            .catch(error => reject(error));
    });

    fetchPromise
        .then(data => {
            toggleDisplayClass(addSystemForm, true)
            toggleDisplayClass(loadingElement, false)

            // Display success or error message
            if (data.success === true) {
                toggleModal(addSystemModal)
                showAlert(data.message, 'success');
                const params = new URLSearchParams(window.location.search);
                const system_id = Number(params.get('system_id'));
                updateSystemSelection(system_id);
            } else {
                toggleModal(addSystemModal)
                showAlert(data.message, 'danger');
                const params = new URLSearchParams(window.location.search);
                const system_id = Number(params.get('system_id'));
                updateSystemSelection(system_id);
            }
        })
        .catch(error => {
            toggleDisplayClass(addSystemForm, true)
            toggleDisplayClass(loadingElement, false)

            showAlert('An error occurred: ' + error.message, 'danger');
        });
});

submitDeleteButton.addEventListener('click', function () {

    const formData = new FormData(deleteSystemForm);
    const deleteSystemModal = document.getElementById('deleteSystemModal')

    toggleDisplayClass(deleteSystemForm, false)

    const loadingElement = document.getElementById('deleteloadingIndicator');
    toggleDisplayClass(loadingElement, true)

    const params = new URLSearchParams({
        delete_system: true
    });

    const fetchPromise = new Promise((resolve, reject) => {
        setTimeout(reject, 180000, new Error('Request timed out'));
        fetch('/admin/save_system?' + params.toString(), {
            method: 'POST',
            body: formData
        })
            .then(response => response.json())
            .then(data => resolve(data))
            .catch(error => reject(error));
    });

    fetchPromise
        .then(data => {
            toggleDisplayClass(deleteSystemForm, true)
            toggleDisplayClass(loadingElement, false)

            // Display success or error message
            if (data.success === true) {
                toggleModal(deleteSystemModal)
                updateSystemSelection();
                querySystem();
                showAlert(data.message, 'success');

            } else {
                toggleModal(deleteSystemModal);
                updateSystemSelection();
                querySystem();
                showAlert(data.message, 'danger');
            }
        })
        .catch(error => {
            toggleDisplayClass(deleteSystemForm, true)
            toggleDisplayClass(loadingElement, false)
            updateSystemSelection();
            querySystem();
            showAlert('An error occurred: ' + error.message, 'danger');
        });
});

submitAddAgencyButton.addEventListener('click', function () {
    const addAgencyModal = document.getElementById('addAgencyModal')
    const formData = new FormData(addAgencyForm);

    toggleDisplayClass(addAgencyForm, false)

    const loadingElement = document.getElementById('addAgencyLoadingIndicator');
    toggleDisplayClass(loadingElement, true)

    const params = new URLSearchParams({
        new_agency: true
    });

    const fetchPromise = new Promise((resolve, reject) => {
        setTimeout(reject, 180000, new Error('Request timed out'));
        fetch('/admin/save_agency?' + params.toString(), {
            method: 'POST',
            body: formData
        })
            .then(response => response.json())
            .then(data => resolve(data))
            .catch(error => reject(error));
    });

    fetchPromise
        .then(data => {
            toggleDisplayClass(addAgencyForm, true)
            toggleDisplayClass(loadingElement, false)

            // Display success or error message
            if (data.success) {
                toggleModal(addAgencyModal)
                showAlert(data.message, 'success');
                setTimeout(function () {
                    location.reload();
                }, 1500);
            } else {
                toggleModal(addAgencyModal)
                showAlert(data.message, 'danger');
            }
        })
        .catch(error => {
            toggleDisplayClass(addAgencyForm, true)
            toggleDisplayClass(loadingElement, false)
            toggleModal(addAgencyModal)
            showAlert('An error occurred: ' + error.message, 'danger');
        });
});

submitDeleteAgencyButton.addEventListener('click', function () {

    const formData = new FormData(deleteAgencyForm);
    const deleteAgencyModal = document.getElementById('deleteAgencyModal')

    toggleDisplayClass(deleteAgencyForm, false)

    const loadingElement = document.getElementById('deleteAgencyLoadingIndicator');
    toggleDisplayClass(loadingElement, true)

    const params = new URLSearchParams({
        delete_agency: true
    });

    const fetchPromise = new Promise((resolve, reject) => {
        setTimeout(reject, 180000, new Error('Request timed out'));
        fetch('/admin/save_agency?' + params.toString(), {
            method: 'POST',
            body: formData
        })
            .then(response => response.json())
            .then(data => resolve(data))
            .catch(error => reject(error));
    });

    fetchPromise
        .then(data => {
            toggleDisplayClass(deleteAgencyForm, true)
            toggleDisplayClass(loadingElement, false)

            // Display success or error message
            if (data.success === true) {
                toggleModal(deleteAgencyModal)
                updateSystemSelection();
                querySystem();
                showAlert(data.message, 'success');

            } else {
                toggleModal(deleteAgencyModal);
                updateSystemSelection();
                querySystem();
                showAlert(data.message, 'danger');
            }
        })
        .catch(error => {
            toggleDisplayClass(deleteAgencyForm, true)
            toggleDisplayClass(loadingElement, false)
            updateSystemSelection();
            querySystem();
            showAlert('An error occurred: ' + error.message, 'danger');
        });
});

document.addEventListener('click', function (e) {
    // Check if the clicked element is an "Add Agency" button
    if (e.target && e.target.id === 'addAgencyButton') {
        // Retrieve system ID from the clicked button
        const systemId = e.target.getAttribute('data-system-id');

        // Find the hidden input in the modal and update its value
        const hiddenInput = document.getElementById('addAgencySystemId');
        if (hiddenInput) {
            hiddenInput.value = systemId;
        }
    }
    else if (e.target && e.target.id === 'deleteAgencyButton') {
        console.log("Delete Agency Button Clicked")
        // Retrieve system ID from the clicked button
        const systemId = e.target.getAttribute('data-system-id');
        const agencyId = e.target.getAttribute('data-agency-id');
        const agencyName = e.target.getAttribute('data-agency-name')

        // Find the hidden input in the modal and update its value
        const hiddenSystemIdInput = document.getElementById('deleteAgencySystemId');
        if (hiddenSystemIdInput) {
            hiddenSystemIdInput.value = systemId;
        }
         const hiddenAgencyIdInput = document.getElementById('deleteAgencyId');
        if (hiddenAgencyIdInput) {
            hiddenAgencyIdInput.value = agencyId;
        }
         const hiddenAgencyNameInput = document.getElementById('deleteAgencyName');
        if (hiddenAgencyNameInput) {
            hiddenAgencyNameInput.value = agencyName;
        }

        const deleteTitle = document.getElementById('deleteAgencyNameTitle')
        if (deleteTitle) {
            deleteTitle.innerText = `Delete ${agencyName}?`
        }

    } else if (e.target && e.target.id === 'deleteSystemButton') {
        // Retrieve system ID from the clicked button
        const systemId = e.target.getAttribute('data-system-id');
        const systemName = e.target.getAttribute('data-system-name')
        const systemShortName = e.target.getAttribute('data-system-short-name')

        // Find the hidden input in the modal and update its value
        const hiddenIdInput = document.getElementById('deleteSystemId');
        if (hiddenIdInput) {
            hiddenIdInput.value = systemId;
        }
        const hiddenNameInput = document.getElementById('deleteSystemName');
        if (hiddenNameInput) {
            hiddenNameInput.value = systemShortName;
        }
        const deleteTitle = document.getElementById('deletesystemNameTitle')
        if (deleteTitle) {
            deleteTitle.innerText = `Delete ${systemName}?`
        }
    }
});
