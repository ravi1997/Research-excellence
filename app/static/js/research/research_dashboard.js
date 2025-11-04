// research_dashboard.js

document.addEventListener('DOMContentLoaded', function() {
    // Fetch and display dashboard statistics
    fetchDashboardStats();
    
    // Fetch and display ongoing research
    fetchOngoingResearch();
    
    // Fetch and display recent publications
    fetchRecentPublications();
    
    // Fetch and display upcoming deadlines
    fetchUpcomingDeadlines();
    
    // Event listeners for action buttons
    document.getElementById('new-project-btn').addEventListener('click', function() {
        window.location.href = '/research/projects/create';
    });
    
    document.getElementById('submit-abstract-btn').addEventListener('click', function() {
        window.location.href = '/research/abstracts/submit';
    });
    
    document.getElementById('submit-award-btn').addEventListener('click', function() {
        window.location.href = '/research/awards/submit';
    });
    
    document.getElementById('view-reports-btn').addEventListener('click', function() {
        window.location.href = '/research/metrics';
    });
});

function fetchDashboardStats() {
    // In a real implementation, this would fetch data from the API
    // For now, we'll use mock data
    document.getElementById('active-projects').textContent = '12';
    document.getElementById('publications').textContent = '45';
    document.getElementById('awards').textContent = '8';
    document.getElementById('citations').textContent = '234';
}

function fetchOngoingResearch() {
    // In a real implementation, this would fetch data from the API
    // For now, we'll use mock data
    const ongoingResearch = [
        { id: 1, title: 'Cancer Research Initiative', status: 'In Progress', progress: 75 },
        { id: 2, title: 'Cardiovascular Disease Study', status: 'In Progress', progress: 40 },
        { id: 3, title: 'Neuroscience Breakthrough', status: 'In Progress', progress: 90 }
    ];
    
    const container = document.getElementById('ongoing-research');
    container.innerHTML = '';
    
    ongoingResearch.forEach(project => {
        const projectElement = document.createElement('div');
        projectElement.className = 'research-item';
        projectElement.innerHTML = `
            <h4>${project.title}</h4>
            <p>Status: ${project.status}</p>
            <div class="progress-bar">
                <div class="progress" style="width: ${project.progress}%"></div>
            </div>
            <p>${project.progress}% Complete</p>
        `;
        container.appendChild(projectElement);
    });
}

function fetchRecentPublications() {
    // In a real implementation, this would fetch data from the API
    // For now, we'll use mock data
    const publications = [
        { id: 1, title: 'Novel Approaches to Cancer Treatment', authors: 'Dr. Smith, Dr. Johnson', journal: 'Nature Medicine', date: '2025-08-15' },
        { id: 2, title: 'Advances in Cardiovascular Surgery', authors: 'Dr. Williams, Dr. Brown', journal: 'The Lancet', date: '2025-07-22' },
        { id: 3, title: 'Neuroplasticity Research', authors: 'Dr. Davis, Dr. Miller', journal: 'Science', date: '2025-06-30' }
    ];
    
    const container = document.getElementById('recent-publications');
    container.innerHTML = '';
    
    publications.forEach(pub => {
        const pubElement = document.createElement('div');
        pubElement.className = 'publication-item';
        pubElement.innerHTML = `
            <h4>${pub.title}</h4>
            <p>Authors: ${pub.authors}</p>
            <p>Journal: ${pub.journal}</p>
            <p>Date: ${pub.date}</p>
        `;
        container.appendChild(pubElement);
    });
}

function fetchUpcomingDeadlines() {
    // In a real implementation, this would fetch data from the API
    // For now, we'll use mock data
    const deadlines = [
        { id: 1, title: 'Abstract Submission Deadline', date: '2025-09-30', daysLeft: 15 },
        { id: 2, title: 'Annual Report Submission', date: '2025-10-15', daysLeft: 30 },
        { id: 3, title: 'Grant Application Deadline', date: '2025-11-01', daysLeft: 47 }
    ];
    
    const container = document.getElementById('upcoming-deadlines');
    container.innerHTML = '';
    
    deadlines.forEach(deadline => {
        const deadlineElement = document.createElement('div');
        deadlineElement.className = 'deadline-item';
        deadlineElement.innerHTML = `
            <h4>${deadline.title}</h4>
            <p>Date: ${deadline.date}</p>
            <p class="days-left">${deadline.daysLeft} days left</p>
        `;
        container.appendChild(deadlineElement);
    });
}