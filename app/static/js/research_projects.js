// research_projects.js

document.addEventListener('DOMContentLoaded', function() {
    // Fetch categories and cycles for filters
    fetchCategories();
    fetchCycles();
    
    // Fetch and display projects
    fetchProjects();
    
    // Event listener for applying filters
    document.getElementById('apply-filters').addEventListener('click', fetchProjects);
    
    // Event listeners for pagination
    document.getElementById('prev-page').addEventListener('click', function() {
        // In a real implementation, this would handle pagination
        console.log('Previous page');
    });
    
    document.getElementById('next-page').addEventListener('click', function() {
        // In a real implementation, this would handle pagination
        console.log('Next page');
    });
});

function fetchCategories() {
    // In a real implementation, this would fetch data from the API
    // For now, we'll use mock data
    const categories = [
        { id: 1, name: 'Medical Research' },
        { id: 2, name: 'Clinical Research' },
        { id: 3, name: 'Public Health' },
        { id: 4, name: 'Biotechnology' }
    ];
    
    const select = document.getElementById('category-filter');
    categories.forEach(category => {
        const option = document.createElement('option');
        option.value = category.id;
        option.textContent = category.name;
        select.appendChild(option);
    });
}

function fetchCycles() {
    // In a real implementation, this would fetch data from the API
    // For now, we'll use mock data
    const cycles = [
        { id: 1, name: '2025 Research Cycle' },
        { id: 2, name: '2024 Research Cycle' },
        { id: 3, name: '2023 Research Cycle' }
    ];
    
    const select = document.getElementById('cycle-filter');
    cycles.forEach(cycle => {
        const option = document.createElement('option');
        option.value = cycle.id;
        option.textContent = cycle.name;
        select.appendChild(option);
    });
}

function fetchProjects() {
    // In a real implementation, this would fetch data from the API
    // For now, we'll use mock data
    const projects = [
        { 
            id: 1, 
            title: 'Cancer Research Initiative', 
            category: 'Medical Research', 
            cycle: '2025 Research Cycle',
            status: 'accepted',
            submissionDate: '2025-09-01'
        },
        { 
            id: 2, 
            title: 'Cardiovascular Disease Study', 
            category: 'Clinical Research', 
            cycle: '2025 Research Cycle',
            status: 'under_review',
            submissionDate: '2025-09-10'
        },
        { 
            id: 3, 
            title: 'Neuroscience Breakthrough', 
            category: 'Medical Research', 
            cycle: '2024 Research Cycle',
            status: 'accepted',
            submissionDate: '2025-08-15'
        }
    ];
    
    const tbody = document.getElementById('projects-table-body');
    tbody.innerHTML = '';
    
    projects.forEach(project => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${project.title}</td>
            <td>${project.category}</td>
            <td>${project.cycle}</td>
            <td><span class="status-${project.status}">${project.status.replace('_', ' ')}</span></td>
            <td>${project.submissionDate}</td>
            <td>
                <button class="btn btn-secondary btn-sm">View</button>
                <button class="btn btn-warning btn-sm">Edit</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}