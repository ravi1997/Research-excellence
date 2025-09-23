// publications.js

document.addEventListener('DOMContentLoaded', function() {
    // Fetch years, categories, and authors for filters
    fetchYears();
    fetchCategories();
    fetchAuthors();
    
    // Fetch and display publications
    fetchPublications();
    
    // Event listener for applying filters
    document.getElementById('apply-filters').addEventListener('click', fetchPublications);
    
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

function fetchAuthors() {
    // In a real implementation, this would fetch data from the API
    // For now, we'll use mock data
    const authors = [
        { id: 1, name: 'Dr. John Smith' },
        { id: 2, name: 'Dr. Jane Johnson' },
        { id: 3, name: 'Dr. Robert Williams' },
        { id: 4, name: 'Dr. Emily Brown' }
    ];
    
    const select = document.getElementById('author-filter');
    authors.forEach(author => {
        const option = document.createElement('option');
        option.value = author.id;
        option.textContent = author.name;
        select.appendChild(option);
    });
}

function fetchPublications() {
    // In a real implementation, this would fetch data from the API
    // For now, we'll use mock data
    const publications = [
        {
            id: 1,
            title: 'Novel Approaches to Cancer Treatment',
            authors: 'Dr. Smith, Dr. Johnson',
            journal: 'Nature Medicine',
            date: '2025-08-15',
            abstract: 'This study explores innovative methods for treating various forms of cancer...',
            citations: 45,
            impactFactor: 32.1
        },
        {
            id: 2,
            title: 'Advances in Cardiovascular Surgery',
            authors: 'Dr. Williams, Dr. Brown',
            journal: 'The Lancet',
            date: '2025-07-22',
            abstract: 'Recent developments in cardiovascular surgical techniques have shown promising results...',
            citations: 32,
            impactFactor: 28.7
        },
        {
            id: 3,
            title: 'Neuroplasticity Research',
            authors: 'Dr. Davis, Dr. Miller',
            journal: 'Science',
            date: '2025-06-30',
            abstract: 'Our research demonstrates significant findings in neuroplasticity and brain recovery...',
            citations: 28,
            impactFactor: 41.2
        }
    ];
    
    const container = document.querySelector('.publications-list');
    
    // Clear existing publications except template
    const template = document.getElementById('publication-template');
    container.innerHTML = '';
    container.appendChild(template);
    
    publications.forEach(pub => {
        const pubElement = template.cloneNode(true);
        pubElement.id = `publication-${pub.id}`;
        pubElement.style.display = 'block';
        
        pubElement.querySelector('.publication-title').textContent = pub.title;
        pubElement.querySelector('.publication-authors').textContent = pub.authors;
        pubElement.querySelector('.publication-journal').textContent = `Journal: ${pub.journal}`;
        pubElement.querySelector('.publication-date').textContent = `Date: ${pub.date}`;
        pubElement.querySelector('.publication-abstract').textContent = pub.abstract;
        pubElement.querySelector('.citation-count .count').textContent = pub.citations;
        pubElement.querySelector('.impact-factor .factor').textContent = pub.impactFactor;
        
        container.appendChild(pubElement);
    });
}