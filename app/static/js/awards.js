// awards.js

document.addEventListener('DOMContentLoaded', function() {
    // Fetch years, categories, and statuses for filters
    fetchYears();
    fetchCategories();
    
    // Fetch and display awards
    fetchAwards();
    
    // Event listener for applying filters
    document.getElementById('apply-filters').addEventListener('click', fetchAwards);
    
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

function fetchYears() {
    // In a real implementation, this would fetch data from the API
    // For now, we'll use mock data
    const years = [2025, 2024, 2023, 2022, 2021];
    
    const select = document.getElementById('year-filter');
    years.forEach(year => {
        const option = document.createElement('option');
        option.value = year;
        option.textContent = year;
        select.appendChild(option);
    });
}

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

function fetchAwards() {
    // In a real implementation, this would fetch data from the API
    // For now, we'll use mock data
    const awards = [
        {
            id: 1,
            title: 'Best Research Paper Award',
            recipient: 'Dr. John Smith',
            category: 'Medical Research',
            date: '2025-09-15',
            description: 'Awarded for outstanding contribution to cancer research',
            status: 'accepted'
        },
        {
            id: 2,
            title: 'Innovation in Healthcare Award',
            recipient: 'Dr. Jane Johnson',
            category: 'Clinical Research',
            date: '2025-08-20',
            description: 'Recognizing innovative approaches to patient care',
            status: 'under_review'
        },
        {
            id: 3,
            title: 'Public Health Excellence Award',
            recipient: 'Dr. Robert Williams',
            category: 'Public Health',
            date: '2025-07-10',
            description: 'Outstanding contribution to public health initiatives',
            status: 'accepted'
        }
    ];
    
    const container = document.querySelector('.awards-list');
    
    // Clear existing awards except template
    const template = document.getElementById('award-template');
    container.innerHTML = '';
    container.appendChild(template);
    
    awards.forEach(award => {
        const awardElement = template.cloneNode(true);
        awardElement.id = `award-${award.id}`;
        awardElement.style.display = 'block';
        
        awardElement.querySelector('.award-title').textContent = award.title;
        awardElement.querySelector('.award-recipient').textContent = award.recipient;
        awardElement.querySelector('.award-category').textContent = `Category: ${award.category}`;
        awardElement.querySelector('.award-date').textContent = `Date: ${award.date}`;
        awardElement.querySelector('.award-description').textContent = award.description;
        awardElement.querySelector('.status-badge').textContent = award.status.replace('_', ' ');
        awardElement.querySelector('.status-badge').className = `status-badge status-${award.status}`;
        
        container.appendChild(awardElement);
    });
}