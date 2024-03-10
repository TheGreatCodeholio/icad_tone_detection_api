/**
 * Utility function to create and return a DOM element with options.
 *
 * @param {string} type - The type of DOM element to create (e.g., 'div', 'input').
 * @param {Object} options - Configuration options for the element.
 * @returns {HTMLElement} The created DOM element.
 */
function createElement(type, options = {}) {
    const element = document.createElement(type);
    if (options.className) element.className = options.className;
    if (options.textContent) element.textContent = options.textContent;
    if (options.innerHTML) element.innerHTML = options.innerHTML;
    if (options.parent) options.parent.appendChild(element);
    if (options.type) element.type = options.type;
    if (options.value) element.value = options.value;
    if (options.id) element.id = options.id;
    if (options.onClick) element.onclick = options.onClick;

    // Set additional attributes if provided
    Object.keys(options.attributes || {}).forEach(key => {
        if (options.attributes[key] !== undefined) { // Check for undefined to allow removal of attributes
            element.setAttribute(key, options.attributes[key]);
        }
    });

    return element;
}

function createFormField(parent, field, systemId, fieldValue) {
    const fieldId = `${field.id}_${systemId}`;
    const { type, label, tooltip, required, options, readOnly } = field;

    // Determine column sizing
    const colSizeClass = (field.id === 'system_api_key' || field.id.endsWith('_enabled')) ? 'col-12' : 'col-md-6';
    const formGroupDiv = document.createElement('div');
    formGroupDiv.className = `${colSizeClass} mb-3`;

    // Create label
    const labelElement = document.createElement('label');
    labelElement.setAttribute('for', fieldId);
    labelElement.className = 'form-label';
    labelElement.textContent = label;
    formGroupDiv.appendChild(labelElement);

    // Input Group for system_api_key
    const inputGroupDiv = document.createElement('div');
    inputGroupDiv.className = 'input-group';

    // Create input, textarea, or select based on type
    let inputElement;
    if (type === 'textarea' || type === 'select') {
        inputElement = document.createElement(type);
        inputElement.setAttribute('rows', '5'); // Only applicable for textarea
    } else {
        inputElement = document.createElement('input');
        inputElement.type = type;
    }

    // Common attributes for input/select/textarea
    inputElement.id = fieldId;
    inputElement.name = field.id;
    inputElement.className = 'form-control';
    inputElement.value = (fieldValue !== null && fieldValue !== undefined) ? fieldValue.toString() : '';
    if (readOnly) inputElement.setAttribute('readonly', true);
    if (required) inputElement.setAttribute('required', '');
    inputElement.setAttribute('data-bs-toggle', 'tooltip');
    inputElement.setAttribute('data-bs-placement', 'top');
    inputElement.setAttribute('title', tooltip);

    // Append input or textarea directly to formGroupDiv, select and input to inputGroupDiv
    if (type === 'select') {
        options.forEach(option => {
            const optionElement = document.createElement('option');
            optionElement.value = option.value;
            optionElement.textContent = option.text;
            if (fieldValue.toString() === option.value) optionElement.selected = true;
            inputElement.appendChild(optionElement);
        });
        inputGroupDiv.appendChild(inputElement); // For select, append to inputGroupDiv
    } else if (type === 'textarea') {
        formGroupDiv.appendChild(inputElement); // For textarea, append directly to formGroupDiv
    } else {
        inputGroupDiv.appendChild(inputElement); // For input, append to inputGroupDiv
    }

    // Special handling for system_api_key with regenerate button
    if (type === 'password') {
        const toggleVisibilityBtn = document.createElement('button');
        toggleVisibilityBtn.type = 'button';
        toggleVisibilityBtn.className = 'btn btn-outline-secondary';
        toggleVisibilityBtn.innerHTML = '<i class="fa-regular fa-eye"></i>'; // Font Awesome Icons eye for showing password
        toggleVisibilityBtn.onclick = function () {
            if (inputElement.type === 'password') {
                inputElement.type = 'text';
                toggleVisibilityBtn.innerHTML = '<i class="fa-solid fa-eye-slash"></i>'; // Change to eye-slash icon
            } else {
                inputElement.type = 'password';
                toggleVisibilityBtn.innerHTML = '<i class="fa-regular fa-eye"></i>'; // Change back to eye icon
            }
        };
        inputGroupDiv.appendChild(inputElement);
        inputGroupDiv.appendChild(toggleVisibilityBtn);
    } else if (type === 'text' && field.id === 'system_api_key') {
        const regenerateBtn = document.createElement('button');
        regenerateBtn.className = 'btn btn-outline-secondary';
        regenerateBtn.type = 'button';
        regenerateBtn.innerHTML = '<i class="fas fa-sync-alt"></i>';
        regenerateBtn.onclick = function () {
            inputElement.value = generateUUIDv4(); // Ensure generateUUIDv4() is defined
        };
        inputGroupDiv.appendChild(regenerateBtn); // Append button to inputGroupDiv
    }

    // Append inputGroupDiv to formGroupDiv if it's used
    if (inputGroupDiv.hasChildNodes()) {
        formGroupDiv.appendChild(inputGroupDiv);
    }

    // Append the form group to the parent container
    parent.appendChild(formGroupDiv);
}