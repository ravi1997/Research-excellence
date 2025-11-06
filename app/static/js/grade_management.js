document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const gradingTypesTab = document.getElementById('gradingTypesTab');
    const gradesTab = document.getElementById('gradesTab');
    const gradingTypesContent = document.getElementById('gradingTypesContent');
    const gradesContent = document.getElementById('gradesContent');
    const gradingTypesTableBody = document.getElementById('gradingTypesTableBody');
    const gradesTableBody = document.getElementById('gradesTableBody');
    const addGradingTypeBtn = document.getElementById('addGradingTypeBtn');
    const addGradeBtn = document.getElementById('addGradeBtn');
    const gradingTypeModal = document.getElementById('gradingTypeModal');
    const gradeModal = document.getElementById('gradeModal');
    const deleteModal = document.getElementById('deleteModal');
    
    // Grading Type Modal Elements
    const closeGradingTypeModal = document.getElementById('closeGradingTypeModal');
    const cancelGradingTypeBtn = document.getElementById('cancelGradingTypeBtn');
    const saveGradingTypeBtn = document.getElementById('saveGradingTypeBtn');
    const gradingTypeForm = document.getElementById('gradingTypeForm');
    const gradingTypeModalTitle = document.getElementById('gradingTypeModalTitle');
    
    // Grade Modal Elements
    const closeGradeModal = document.getElementById('closeGradeModal');
    const cancelGradeBtn = document.getElementById('cancelGradeBtn');
    const saveGradeBtn = document.getElementById('saveGradeBtn');
    const gradeForm = document.getElementById('gradeForm');
    const gradeModalTitle = document.getElementById('gradeModalTitle');
    
    // Delete Modal Elements
    const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
    const cancelDeleteBtn = document.getElementById('cancelDeleteBtn');
    
    // Form Inputs
    const criteriaInput = document.getElementById('criteria');
    const gradingForInput = document.getElementById('gradingFor');
    const minScoreInput = document.getElementById('minScore');
    const maxScoreInput = document.getElementById('maxScore');
    const verificationLevelInput = document.getElementById('verificationLevel');
    
    const gradingTypeSelect = document.getElementById('gradingTypeSelect');
    const submissionTypeInput = document.getElementById('submissionType');
    const submissionIdInput = document.getElementById('submissionId');
    const gradeScoreInput = document.getElementById('gradeScore');
    const gradeCommentsInput = document.getElementById('gradeComments');
    
    // State variables
    let currentGradingType = null;
    let currentGrade = null;
    let currentDeleteItem = null;
    let currentDeleteType = null; // 'grading-type' or 'grade'
    let gradingTypesCache = [];
    
    // Initialize the page
    init();
    
    function init() {
        setupEventListeners();
        switchTab('grading-types');
        loadGradingTypes();
        loadGrades();
    }
    
    function setupEventListeners() {
        // Tab switching
        gradingTypesTab.addEventListener('click', () => switchTab('grading-types'));
        gradesTab.addEventListener('click', () => switchTab('grades'));
        
        // Modal close buttons
        closeGradingTypeModal.addEventListener('click', () => closeModal('grading-type'));
        cancelGradingTypeBtn.addEventListener('click', () => closeModal('grading-type'));
        closeGradeModal.addEventListener('click', () => closeModal('grade'));
        cancelGradeBtn.addEventListener('click', () => closeModal('grade'));
        cancelDeleteBtn.addEventListener('click', () => closeModal('delete'));
        
        gradingTypeModal.addEventListener('click', (event) => {
            if (event.target === gradingTypeModal) closeModal('grading-type');
        });
        gradeModal.addEventListener('click', (event) => {
            if (event.target === gradeModal) closeModal('grade');
        });
        deleteModal.addEventListener('click', (event) => {
            if (event.target === deleteModal) closeModal('delete');
        });
        
        // Save buttons
        saveGradingTypeBtn.addEventListener('click', saveGradingType);
        saveGradeBtn.addEventListener('click', saveGrade);
        confirmDeleteBtn.addEventListener('click', deleteItem);
        
        // Add grading type button
        addGradingTypeBtn.addEventListener('click', () => openModal('grading-type'));
        
        if (addGradeBtn) {
            addGradeBtn.addEventListener('click', () => openModal('grade'));
        }
        
        // Dismiss modals with Escape
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') {
                if (!gradingTypeModal.classList.contains('hidden')) closeModal('grading-type');
                if (!gradeModal.classList.contains('hidden')) closeModal('grade');
                if (!deleteModal.classList.contains('hidden')) closeModal('delete');
            }
        });
    }
    
    function switchTab(tabName) {
        const isCriteria = tabName === 'grading-types';
        
        toggleTabButton(gradingTypesTab, isCriteria);
        toggleTabButton(gradesTab, !isCriteria);
        
        gradingTypesContent.classList.toggle('hidden', !isCriteria);
        gradesContent.classList.toggle('hidden', isCriteria);
    }
    
    function openModal(type, item = null) {
        if (type === 'grading-type') {
            currentGradingType = item;
            gradingTypeModalTitle.textContent = item ? 'Edit Grading Criteria' : 'Add Grading Criteria';
            resetGradingTypeForm();
            
            if (item) {
                criteriaInput.value = item.criteria;
                gradingForInput.value = item.grading_for;
                minScoreInput.value = item.min_score;
                maxScoreInput.value = item.max_score;
                verificationLevelInput.value = item.verification_level;
            }
            
            showModal(gradingTypeModal);
        } else if (type === 'grade') {
            if (!gradingTypesCache || gradingTypesCache.length === 0) {
                showNotification('Please create a grading criteria before adding grades.', 'error');
                return;
            }
            currentGrade = item;
            gradeModalTitle.textContent = item ? 'Edit Grade' : 'Add Grade';
            populateGradingTypeSelect(gradingTypesCache);
            resetGradeForm();
            
            if (item) {
                // Populate form with existing grade data
                gradingTypeSelect.value = item.grading_type_id;
                submissionTypeInput.value = getSubmissionType(item);
                submissionIdInput.value = getSubmissionId(item);
                gradeScoreInput.value = item.score;
                gradeCommentsInput.value = item.comments || '';
            }
            
            showModal(gradeModal);
        }
    }
    
    function closeModal(type) {
        if (type === 'grading-type') {
            hideModal(gradingTypeModal);
            currentGradingType = null;
        } else if (type === 'grade') {
            hideModal(gradeModal);
            currentGrade = null;
        } else if (type === 'delete') {
            hideModal(deleteModal);
            currentDeleteItem = null;
            currentDeleteType = null;
        }
    }
    
    function resetGradingTypeForm() {
        if (gradingTypeForm) {
            gradingTypeForm.reset();
        }
        const gradingTypeError = document.getElementById('gradingTypeError');
        if (gradingTypeError) {
            gradingTypeError.classList.add('hidden');
        }
    }
    
    function resetGradeForm() {
        if (gradeForm) {
            gradeForm.reset();
        }
        const gradeError = document.getElementById('gradeError');
        if (gradeError) {
            gradeError.classList.add('hidden');
        }
    }
    
    function showModal(modal) {
        if (!modal) return;
        modal.classList.remove('hidden');
        modal.style.display = 'block';
        document.body.classList.add('overflow-hidden');
    }
    
    function hideModal(modal) {
        if (!modal) return;
        modal.classList.add('hidden');
        modal.style.display = 'none';
        document.body.classList.remove('overflow-hidden');
    }
    
    function getSubmissionType(grade) {
        if (grade.abstract_id) return 'abstract';
        if (grade.award_id) return 'award';
        if (grade.best_paper_id) return 'best_paper';
        return '';
    }
    
    function getSubmissionId(grade) {
        if (grade.abstract_id) return grade.abstract_id;
        if (grade.award_id) return grade.award_id;
        if (grade.best_paper_id) return grade.best_paper_id;
        return '';
    }
    
    async function loadGradingTypes() {
        try {
            const response = await fetch('/api/v1/research/grading-types', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token') || sessionStorage.getItem('authToken')}`
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            gradingTypesCache = Array.isArray(data) ? data : [];
            renderGradingTypes(gradingTypesCache);
            populateGradingTypeSelect(gradingTypesCache);
        } catch (error) {
            console.error('Error loading grading types:', error);
            showNotification('Failed to load grading types', 'error');
        }
    }
    
    async function loadGrades() {
        try {
            const response = await fetch('/api/v1/research/gradings', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token') || sessionStorage.getItem('authToken')}`
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            renderGrades(data);
        } catch (error) {
            console.error('Error loading grades:', error);
            showNotification('Failed to load grades', 'error');
        }
    }
    
    function renderGradingTypes(gradingTypes) {
        gradingTypesTableBody.innerHTML = '';
        
        if (!gradingTypes.length) {
            gradingTypesTableBody.appendChild(createEmptyRow(6, 'No grading criteria yet. Add one to get started.'));
            return;
        }
        
        gradingTypes.forEach(type => {
            const row = document.createElement('tr');
            row.className = 'bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-800';
            
            row.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">${type.criteria}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">${type.grading_for}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">${type.min_score}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">${type.max_score}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">${type.verification_level}</td>
                <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <button class="edit-grading-type text-blue-600 hover:text-blue-900 dark:text-blue-400 dark:hover:text-blue-300 mr-3" data-id="${type.id}">Edit</button>
                    <button class="delete-grading-type text-red-600 hover:text-red-900 dark:text-red-400 dark:hover:text-red-300" data-id="${type.id}">Delete</button>
                </td>
            `;
            
            gradingTypesTableBody.appendChild(row);
        });
        
        // Add event listeners to edit and delete buttons
        document.querySelectorAll('.edit-grading-type').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = e.target.dataset.id;
                const type = gradingTypes.find(t => t.id === id);
                openModal('grading-type', type);
            });
        });
        
        document.querySelectorAll('.delete-grading-type').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = e.target.dataset.id;
                const type = gradingTypes.find(t => t.id === id);
                openDeleteModal('grading-type', type);
            });
        });
    }
    
    function populateGradingTypeSelect(gradingTypes) {
        if (!gradingTypeSelect) return;
        
        gradingTypeSelect.innerHTML = '<option value="">Select grading criteria</option>';
        
        gradingTypes.forEach(type => {
            const option = document.createElement('option');
            option.value = type.id;
            option.textContent = type.criteria;
            gradingTypeSelect.appendChild(option);
        });
        
        if (!gradingTypes.length) {
            const noOption = document.createElement('option');
            noOption.value = '';
            noOption.textContent = 'No grading criteria available';
            noOption.disabled = true;
            gradingTypeSelect.appendChild(noOption);
        }
    }
    
    function renderGrades(grades) {
        gradesTableBody.innerHTML = '';
        
        if (!grades.length) {
            gradesTableBody.appendChild(createEmptyRow(6, 'No grades recorded yet.'));
            return;
        }
        
        grades.forEach(grade => {
            const row = document.createElement('tr');
            row.className = 'bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-800';
            
            // Get submission type and ID
            let submissionType = '';
            let submissionId = '';
            if (grade.abstract_id) {
                submissionType = 'Abstract';
                submissionId = grade.abstract_id;
            } else if (grade.award_id) {
                submissionType = 'Award';
                submissionId = grade.award_id;
            } else if (grade.best_paper_id) {
                submissionType = 'Best Paper';
                submissionId = grade.best_paper_id;
            }
            
            row.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">${grade.grading_type?.criteria || 'N/A'}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">${formatSubmission(submissionType, submissionId)}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">${grade.score}</td>
                <td class="px-6 py-4 text-sm text-gray-500 dark:text-gray-400 max-w-xs truncate">${grade.comments || 'No comments'}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">${grade.graded_by?.name || 'N/A'}</td>
                <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <button class="edit-grade text-blue-600 hover:text-blue-900 dark:text-blue-400 dark:hover:text-blue-300 mr-3" data-id="${grade.id}">Edit</button>
                    <button class="delete-grade text-red-600 hover:text-red-900 dark:text-red-400 dark:hover:text-red-300" data-id="${grade.id}">Delete</button>
                </td>
            `;
            
            gradesTableBody.appendChild(row);
        });
        
        // Add event listeners to edit and delete buttons
        document.querySelectorAll('.edit-grade').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = e.target.dataset.id;
                const grade = grades.find(g => g.id === id);
                openModal('grade', grade);
            });
        });
        
        document.querySelectorAll('.delete-grade').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = e.target.dataset.id;
                const grade = grades.find(g => g.id === id);
                openDeleteModal('grade', grade);
            });
        });
    }
    
    async function saveGradingType() {
        const criteria = criteriaInput.value.trim();
        const gradingFor = gradingForInput.value;
        const minScore = parseInt(minScoreInput.value);
        const maxScore = parseInt(maxScoreInput.value);
        const verificationLevel = parseInt(verificationLevelInput.value);
        
        if (!criteria || !gradingFor || isNaN(minScore) || isNaN(maxScore) || isNaN(verificationLevel)) {
            showNotification('Please fill in all fields', 'error');
            return;
        }
        
        if (minScore >= maxScore) {
            showNotification('Min score must be less than max score', 'error');
            return;
        }
        
        try {
            let response;
            if (currentGradingType) {
                // Update existing grading type
                response = await fetch(`/api/v1/research/grading-types/${currentGradingType.id}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${localStorage.getItem('token') || sessionStorage.getItem('authToken')}`
                    },
                    body: JSON.stringify({
                        criteria,
                        grading_for: gradingFor,
                        min_score: minScore,
                        max_score: maxScore,
                        verification_level: verificationLevel
                    })
                });
            } else {
                // Create new grading type
                response = await fetch('/api/v1/research/grading-types', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${localStorage.getItem('token') || sessionStorage.getItem('authToken')}`
                    },
                    body: JSON.stringify({
                        criteria,
                        grading_for: gradingFor,
                        min_score: minScore,
                        max_score: maxScore,
                        verification_level: verificationLevel
                    })
                });
            }
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            showNotification(currentGradingType ? 'Grading criteria updated successfully' : 'Grading criteria added successfully');
            closeModal('grading-type');
            loadGradingTypes();
        } catch (error) {
            console.error('Error saving grading type:', error);
            showNotification(`Failed to ${currentGradingType ? 'update' : 'add'} grading criteria: ${error.message}`, 'error');
        }
    }
    
    async function saveGrade() {
        const gradingTypeId = gradingTypeSelect.value;
        const submissionType = submissionTypeInput.value;
        const submissionId = submissionIdInput.value.trim();
        const score = parseInt(gradeScoreInput.value);
        const comments = gradeCommentsInput.value.trim();
        
        if (!gradingTypeId || !submissionType || !submissionId || isNaN(score)) {
            showNotification('Please fill in all required fields', 'error');
            return;
        }
        
        if (score < 0) {
            showNotification('Score cannot be negative.', 'error');
            return;
        }
        
        try {
            // Prepare the payload based on submission type
            const payload = {
                grading_type_id: gradingTypeId,
                score,
                comments: comments || null
            };
            
            // Set the appropriate submission ID based on type
            if (submissionType === 'abstract') {
                payload.abstract_id = submissionId;
            } else if (submissionType === 'award') {
                payload.award_id = submissionId;
            } else if (submissionType === 'best_paper') {
                payload.best_paper_id = submissionId;
            }
            
            let response;
            if (currentGrade) {
                // Update existing grade
                response = await fetch(`/api/v1/research/gradings/${currentGrade.id}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${localStorage.getItem('token') || sessionStorage.getItem('authToken')}`
                    },
                    body: JSON.stringify(payload)
                });
            } else {
                // Create new grade
                response = await fetch('/api/v1/research/gradings', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${localStorage.getItem('token') || sessionStorage.getItem('authToken')}`
                    },
                    body: JSON.stringify(payload)
                });
            }
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            showNotification(currentGrade ? 'Grade updated successfully' : 'Grade added successfully');
            closeModal('grade');
            loadGrades();
        } catch (error) {
            console.error('Error saving grade:', error);
            showNotification(`Failed to ${currentGrade ? 'update' : 'add'} grade: ${error.message}`, 'error');
        }
    }
    
    function openDeleteModal(type, item) {
        currentDeleteItem = item;
        currentDeleteType = type;
        document.getElementById('deleteModalTitle').textContent = 
            `Delete ${type === 'grading-type' ? 'Grading Criteria' : 'Grade'}`;
        showModal(deleteModal);
    }
    
    async function deleteItem() {
        if (!currentDeleteItem || !currentDeleteType) return;
        
        try {
            let response;
            if (currentDeleteType === 'grading-type') {
                response = await fetch(`/api/v1/research/grading-types/${currentDeleteItem.id}`, {
                    method: 'DELETE',
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('token') || sessionStorage.getItem('authToken')}`
                    }
                });
            } else if (currentDeleteType === 'grade') {
                response = await fetch(`/api/v1/research/gradings/${currentDeleteItem.id}`, {
                    method: 'DELETE',
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('token') || sessionStorage.getItem('authToken')}`
                    }
                });
            }
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
            }
            
            showNotification(`${currentDeleteType === 'grading-type' ? 'Grading criteria' : 'Grade'} deleted successfully`);
            closeModal('delete');
            
            if (currentDeleteType === 'grading-type') {
                loadGradingTypes();
            } else {
                loadGrades();
            }
        } catch (error) {
            console.error(`Error deleting ${currentDeleteType}:`, error);
            showNotification(`Failed to delete ${currentDeleteType === 'grading-type' ? 'grading criteria' : 'grade'}: ${error.message}`, 'error');
        }
    }
    
    function showNotification(message, type = 'success') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 p-4 rounded-md shadow-lg z-50 ${
            type === 'success' ? 'bg-green-500 text-white' : 'bg-red-500 text-white'
        }`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // Remove notification after 3 seconds
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 3000);
    }
    
    // Add active tab styling
    const activeTabStyle = document.createElement('style');
    activeTabStyle.textContent = `
        .active-tab {
            border-color: #3B82F6 !important;
            color: #2563EB !important;
        }
    `;
    document.head.appendChild(activeTabStyle);
    
    function toggleTabButton(button, isActive) {
        const baseClasses = [
            'whitespace-nowrap',
            'border-b-2',
            'px-1',
            'py-3',
            'text-sm',
            'font-medium',
            'transition',
            'focus:outline-none',
            'focus-visible:ring-2',
            'focus-visible:ring-blue-500',
            'focus-visible:ring-offset-2',
            'dark:focus-visible:ring-offset-gray-900'
        ];
        
        if (isActive) {
            button.className = [
                ...baseClasses,
                'border-blue-500',
                'text-blue-600',
                'active-tab'
            ].join(' ');
        } else {
            button.className = [
                ...baseClasses,
                'border-transparent',
                'text-gray-500',
                'hover:border-gray-300',
                'hover:text-gray-700',
                'dark:text-gray-400',
                'dark:hover:text-gray-200'
            ].join(' ');
        }
    }
    
    function createEmptyRow(colspan, message) {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td colspan="${colspan}" class="px-6 py-8 text-center text-sm text-gray-500 dark:text-gray-400">
                ${message}
            </td>
        `;
        return row;
    }
    
    function formatSubmission(type, id) {
        if (!type || !id) {
            return '—';
        }
        
        const trimmed = id.length > 12 ? `${id.slice(0, 12)}…` : id;
        return `${type} (${trimmed})`;
    }
});
