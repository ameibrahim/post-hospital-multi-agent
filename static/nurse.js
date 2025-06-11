// Nurse Dashboard JavaScript Functions

let patientToDelete = null;

function addMedication() {
    const container = document.getElementById('medications');
    const newRow = document.createElement('div');
    newRow.className = 'medication-row';
    newRow.innerHTML = `
        <input type="text" placeholder="Medicine name" class="med-name">
        <input type="text" placeholder="Dosage" class="med-dosage">
        <input type="text" placeholder="Frequency" class="med-frequency">
        <button type="button" onclick="this.parentElement.remove()" class="btn btn-danger btn-sm">Remove</button>
    `;
    container.appendChild(newRow);
}

// Handle patient creation form submission
document.getElementById('createPatientForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const medications = [];
    
    // Collect medication data
    document.querySelectorAll('.medication-row').forEach(row => {
        const name = row.querySelector('.med-name').value;
        const dosage = row.querySelector('.med-dosage').value;
        const frequency = row.querySelector('.med-frequency').value;
        
        if (name && dosage && frequency) {
            medications.push({ name, dosage, frequency });
        }
    });
    
    const data = {
        name: formData.get('name'),
        email: formData.get('email'),
        patient_id: formData.get('patient_id'),
        conditions: formData.get('conditions').split(',').map(s => s.trim()).filter(s => s),
        medications: medications,
        allergies: formData.get('allergies').split(',').map(s => s.trim()).filter(s => s),
        discharge_plan: formData.get('discharge_plan')
    };
    
    // Validate required fields
    if (!data.name || !data.email || !data.patient_id) {
        alert('Patient name, email, and ID are required');
        return;
    }
    
    // Validate email format
    if (!isValidEmail(data.email)) {
        alert('Please enter a valid email address');
        return;
    }
    
    // Show loading state
    const submitBtn = e.target.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    submitBtn.textContent = 'Creating patient and sending email...';
    submitBtn.disabled = true;
    
    try {
        const response = await fetch('/api/create_patient', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            let message = `Patient agent created successfully for ${data.name}!`;
            
            // Add warnings if any services failed
            if (result.warnings) {
                if (result.warnings.letta_agent) {
                    message += '\n\n⚠️ Warning: AI agent creation failed - patient can still login but chat may not work.';
                }
                if (result.warnings.email_delivery) {
                    message += '\n\n⚠️ Warning: Email delivery failed - please share credentials manually:';
                    message += `\nEmail: ${data.email}`;
                    message += `\nPassword: ${result.password}`;
                    message += `\nMagic Token: ${result.magic_token}`;
                }
            } else {
                message += `\n\nCredentials and medical summary have been sent to ${data.email}`;
            }
            
            alert(message);
            location.reload();
        } else {
            alert('Error: ' + result.error);
        }
    } catch (error) {
        console.error('Error creating patient:', error);
        alert('Error creating patient: ' + error.message);
    } finally {
        submitBtn.textContent = originalText;
        submitBtn.disabled = false;
    }
});

async function sendInstruction(patientName) {
    const textarea = document.querySelector(`[data-patient="${patientName}"]`);
    const instruction = textarea.value.trim();
    
    if (!instruction) {
        alert('Please enter an instruction');
        return;
    }
    
    try {
        const response = await fetch('/api/send_instruction', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                patient_name: patientName,
                instruction: instruction
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert(`Instruction sent successfully to ${patientName}!`);
            textarea.value = '';
        } else {
            alert('Error: ' + result.error);
        }
    } catch (error) {
        console.error('Error sending instruction:', error);
        alert('Error sending instruction: ' + error.message);
    }
}

function confirmDeletePatient(patientName) {
    patientToDelete = patientName;
    document.getElementById('deletePatientName').textContent = patientName;
    document.getElementById('deleteModal').style.display = 'flex';
}

function closeDeleteModal() {
    patientToDelete = null;
    document.getElementById('deleteModal').style.display = 'none';
}

async function deletePatient() {
    if (!patientToDelete) return;
    
    try {
        const response = await fetch('/api/delete_patient', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ patient_name: patientToDelete })
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert(`Patient ${patientToDelete} deleted successfully!`);
            location.reload();
        } else {
            alert('Error: ' + result.error);
        }
    } catch (error) {
        console.error('Error deleting patient:', error);
        alert('Error deleting patient: ' + error.message);
    } finally {
        closeDeleteModal();
    }
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('deleteModal');
    if (event.target === modal) {
        closeDeleteModal();
    }
}

// Form validation helpers
function validatePatientId(input) {
    const value = input.value;
    const isValid = /^[A-Za-z0-9]+$/.test(value);
    
    if (!isValid && value.length > 0) {
        input.style.borderColor = '#dc3545';
        showValidationError(input, 'Patient ID can only contain letters and numbers');
    } else {
        input.style.borderColor = '#ddd';
        hideValidationError(input);
    }
}

function validateEmail(input) {
    const email = input.value;
    const isValid = isValidEmail(email);
    
    if (!isValid && email.length > 0) {
        input.style.borderColor = '#dc3545';
        showValidationError(input, 'Please enter a valid email address');
    } else {
        input.style.borderColor = '#ddd';
        hideValidationError(input);
    }
}

function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

function showValidationError(input, message) {
    let errorDiv = input.parentNode.querySelector('.validation-error');
    if (!errorDiv) {
        errorDiv = document.createElement('div');
        errorDiv.className = 'validation-error';
        errorDiv.style.color = '#dc3545';
        errorDiv.style.fontSize = '12px';
        errorDiv.style.marginTop = '5px';
        input.parentNode.appendChild(errorDiv);
    }
    errorDiv.textContent = message;
}

function hideValidationError(input) {
    const errorDiv = input.parentNode.querySelector('.validation-error');
    if (errorDiv) {
        errorDiv.remove();
    }
}

// Add event listeners for validation
document.addEventListener('DOMContentLoaded', function() {
    const patientIdInput = document.querySelector('input[name="patient_id"]');
    if (patientIdInput) {
        patientIdInput.addEventListener('input', function() {
            validatePatientId(this);
        });
    }
    
    const emailInput = document.querySelector('input[name="email"]');
    if (emailInput) {
        emailInput.addEventListener('input', function() {
            validateEmail(this);
        });
    }
});