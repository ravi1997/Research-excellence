// API base URL
const API_BASE_URL = '/api/v1/research';

// DOM Elements
const cycleTableBody = document.getElementById('cycleTableBody');
const cycleDetailSection = document.getElementById('cycleDetailSection');
const cycleDetailName = document.getElementById('cycleDetailName');
const cycleWindowsContainer = document.getElementById('cycleWindowsContainer');
const cycleIdForWindow = document.getElementById('cycleIdForWindow');
const addWindowForm = document.getElementById('addWindowForm');
const cycleForm = document.getElementById('cycleForm');
const cycleModal = document.getElementById('cycleModal');
const modalTitle = document.getElementById('modalTitle');
const cycleIdInput = document.getElementById('cycleId');
const cycleNameInput = document.getElementById('cycleName');
const cycleStartDateInput = document.getElementById('cycleStartDate');
const cycleEndDateInput = document.getElementById('cycleEndDate');
const createCycleBtn = document.getElementById('createCycleBtn');
const backToCyclesBtn = document.getElementById('backToCyclesBtn');
const closeModalBtn = document.getElementById('closeModalBtn');
const cancelModalBtn = document.getElementById('cancelModalBtn');

// Initialize the page
document.addEventListener('DOMContentLoaded', function() {
    loadCycles();
    
    // Event listeners
    createCycleBtn.addEventListener('click', openCreateCycleModal);
    backToCyclesBtn.addEventListener('click', showCycleList);
    closeModalBtn.addEventListener('click', closeCycleModal);
    cancelModalBtn.addEventListener('click', closeCycleModal);
    cycleForm.addEventListener('submit', handleCycleFormSubmit);
    addWindowForm.addEventListener('submit', handleAddWindow);
    
    // Event delegation for dynamic buttons
    cycleTableBody.addEventListener('click', function(e) {
        if (e.target.classList.contains('view-cycle-btn')) {
            const cycleId = e.target.getAttribute('data-cycle-id');
            viewCycleDetails(cycleId);
        } else if (e.target.classList.contains('edit-cycle-btn')) {
            const cycleId = e.target.getAttribute('data-cycle-id');
            editCycle(cycleId);
        } else if (e.target.classList.contains('delete-cycle-btn')) {
            const cycleId = e.target.getAttribute('data-cycle-id');
            deleteCycle(cycleId);
        }
    });
    
    cycleWindowsContainer.addEventListener('click', function(e) {
        if (e.target.classList.contains('delete-window-btn')) {
            const cycleId = e.target.getAttribute('data-cycle-id');
            const windowId = e.target.getAttribute('data-window-id');
            deleteWindow(cycleId, windowId);
        }
    });
});

// Load all cycles
async function loadCycles() {
    try {
        const response = await fetch(`${API_BASE_URL}/cycles`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token') || sessionStorage.getItem('access_token')}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const cycles = await response.json();
        renderCycleList(cycles);
    } catch (error) {
        console.error('Error loading cycles:', error);
        alert('Error loading cycles: ' + error.message);
    }
}

// Render cycle list in table
function renderCycleList(cycles) {
    cycleTableBody.innerHTML = '';
    
    cycles.forEach(cycle => {
        const row = document.createElement('tr');
        
        // Format dates
        const startDate = new Date(cycle.start_date).toLocaleDateString();
        const endDate = new Date(cycle.end_date).toLocaleDateString();
        
        row.innerHTML = `
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-800">${cycle.name}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${startDate}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${endDate}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                <button class="view-cycle-btn text-blue-600 hover:text-blue-900 mr-3" data-cycle-id="${cycle.id}">View Windows</button>
                <button class="edit-cycle-btn text-green-600 hover:text-green-900 mr-3" data-cycle-id="${cycle.id}">Edit</button>
                <button class="delete-cycle-btn text-red-600 hover:text-red-900" data-cycle-id="${cycle.id}">Delete</button>
            </td>
        `;
        
        cycleTableBody.appendChild(row);
    });
}

// View cycle details and windows
async function viewCycleDetails(cycleId) {
    try {
        // Get cycle details
        const cycleResponse = await fetch(`${API_BASE_URL}/cycles/${cycleId}`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token') || sessionStorage.getItem('access_token')}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (!cycleResponse.ok) {
            throw new Error(`HTTP error! status: ${cycleResponse.status}`);
        }
        
        const cycle = await cycleResponse.json();
        
        // Get cycle windows
        const windowsResponse = await fetch(`${API_BASE_URL}/cycles/${cycleId}/windows`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token') || sessionStorage.getItem('access_token')}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (!windowsResponse.ok) {
            throw new Error(`HTTP error! status: ${windowsResponse.status}`);
        }
        
        const windows = await windowsResponse.json();
        
        // Show cycle detail section
        cycleDetailName.textContent = cycle.data.name;
        cycleIdForWindow.value = cycleId;
        renderCycleWindows(windows.data);
        
        document.querySelector('.bg-white.rounded-lg.shadow-md.p-6.mb-8:first-child').classList.add('hidden');
        cycleDetailSection.classList.remove('hidden');
    } catch (error) {
        console.error('Error loading cycle details:', error);
        alert('Error loading cycle details: ' + error.message);
    }
}

// Render cycle windows
function renderCycleWindows(windows) {
    if (windows.length === 0) {
        cycleWindowsContainer.innerHTML = '<p class="text-gray-600">No time windows defined for this cycle.</p>';
        return;
    }
    
    let html = '<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">';
    
    windows.forEach(window => {
        // Format phase name for display
        const phaseDisplay = formatPhaseName(window.phase);
        const startDate = new Date(window.start_date).toLocaleDateString();
        const endDate = new Date(window.end_date).toLocaleDateString();
        
        html += `
            <div class="border border-gray-200 rounded-lg p-4 bg-gray-50">
                <div class="flex justify-between items-start">
                    <div>
                        <h4 class="font-medium text-gray-800">${phaseDisplay}</h4>
                        <p class="text-sm text-gray-600">${startDate} to ${endDate}</p>
                    </div>
                    <button class="delete-window-btn text-red-600 hover:text-red-800" data-cycle-id="${window.cycle_id}" data-window-id="${window.id}">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                        </svg>
                    </button>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    cycleWindowsContainer.innerHTML = html;
}

// Format phase name for display
function formatPhaseName(phase) {
    const phaseNames = {
        'SUBMISSION': 'General Submission',
        'VERIFICATION': 'General Verification',
        'FINAL': 'General Final',
        'ABSTRACT_SUBMISSION': 'Abstract Submission',
        'ABSTRACT_VERIFICATION': 'Abstract Verification',
        'ABSTRACT_FINAL': 'Abstract Final',
        'BEST_PAPER_SUBMISSION': 'Best Paper Submission',
        'BEST_PAPER_VERIFICATION': 'Best Paper Verification',
        'BEST_PAPER_FINAL': 'Best Paper Final',
        'AWARD_SUBMISSION': 'Award Submission',
        'AWARD_VERIFICATION': 'Award Verification',
        'AWARD_FINAL': 'Award Final'
    };
    
    return phaseNames[phase] || phase;
}

// Show cycle list view
function showCycleList() {
    document.querySelector('.bg-white.rounded-lg.shadow-md.p-6.mb-8:first-child').classList.remove('hidden');
    cycleDetailSection.classList.add('hidden');
}

// Open create cycle modal
function openCreateCycleModal() {
    modalTitle.textContent = 'Create New Cycle';
    cycleForm.reset();
    cycleIdInput.value = '';
    cycleModal.classList.remove('hidden');
}

// Edit cycle
async function editCycle(cycleId) {
    try {
        const response = await fetch(`${API_BASE_URL}/cycles/${cycleId}`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token') || sessionStorage.getItem('access_token')}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const cycle = await response.json();
        
        modalTitle.textContent = 'Edit Cycle';
        cycleIdInput.value = cycle.data.id;
        cycleNameInput.value = cycle.data.name;
        cycleStartDateInput.value = cycle.data.start_date;
        cycleEndDateInput.value = cycle.data.end_date;
        
        cycleModal.classList.remove('hidden');
    } catch (error) {
        console.error('Error loading cycle for edit:', error);
        alert('Error loading cycle: ' + error.message);
    }
}

// Handle cycle form submission
async function handleCycleFormSubmit(e) {
    e.preventDefault();
    
    const cycleData = {
        name: cycleNameInput.value,
        start_date: cycleStartDateInput.value,
        end_date: cycleEndDateInput.value
    };
    
    const cycleId = cycleIdInput.value;
    const method = cycleId ? 'PUT' : 'POST';
    const url = cycleId ? `${API_BASE_URL}/cycles/${cycleId}` : `${API_BASE_URL}/cycles`;
    
    try {
        const response = await fetch(url, {
            method: method,
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token') || sessionStorage.getItem('access_token')}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(cycleData)
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        closeCycleModal();
        loadCycles();
        
        // If we were editing a cycle, refresh the detail view too
        if (!cycleDetailSection.classList.contains('hidden') && cycleId) {
            viewCycleDetails(cycleId);
        }
    } catch (error) {
        console.error('Error saving cycle:', error);
        alert('Error saving cycle: ' + error.message);
    }
}

// Close cycle modal
function closeCycleModal() {
    cycleModal.classList.add('hidden');
}

// Delete cycle
async function deleteCycle(cycleId) {
    if (!confirm('Are you sure you want to delete this cycle? This will also delete all associated windows.')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/cycles/${cycleId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token') || sessionStorage.getItem('access_token')}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        loadCycles();
    } catch (error) {
        console.error('Error deleting cycle:', error);
        alert('Error deleting cycle: ' + error.message);
    }
}

// Handle add window form submission
async function handleAddWindow(e) {
    e.preventDefault();
    
    const windowData = {
        phase: document.getElementById('windowPhase').value,
        start_date: document.getElementById('windowStartDate').value,
        end_date: document.getElementById('windowEndDate').value
    };
    
    if (!windowData.phase || !windowData.start_date || !windowData.end_date) {
        alert('Please fill in all fields');
        return;
    }
    
    const cycleId = cycleIdForWindow.value;
    
    try {
        const response = await fetch(`${API_BASE_URL}/cycles/${cycleId}/windows`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token') || sessionStorage.getItem('access_token')}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(windowData)
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        addWindowForm.reset();
        viewCycleDetails(cycleId); // Refresh the view
    } catch (error) {
        console.error('Error adding window:', error);
        alert('Error adding window: ' + error.message);
    }
}

// Delete window
async function deleteWindow(cycleId, windowId) {
    if (!confirm('Are you sure you want to delete this time window?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/cycles/${cycleId}/windows/${windowId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token') || sessionStorage.getItem('access_token')}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        viewCycleDetails(cycleId); // Refresh the view
    } catch (error) {
        console.error('Error deleting window:', error);
        alert('Error deleting window: ' + error.message);
    }
}