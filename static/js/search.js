
document.addEventListener('DOMContentLoaded', function () {
    const searchForm = document.getElementById('searchForm');
    const searchQuery = document.getElementById('searchQuery');
    const searchResults = document.getElementById('searchResults');
    const paginationContainer = document.getElementById('pagination');

    // Filter elements
    const examFilter = document.getElementById('examFilter');
    const subjectFilter = document.getElementById('subjectFilter');
    const chapterFilter = document.getElementById('chapterFilter');
    const paperFilter = document.getElementById('paperFilter');

    // Store selected filter values
    let selectedExams = [];
    let selectedSubjects = [];
    let selectedChapters = [];
    let selectedPapers = [];

    // Initial query from URL
    const urlParams = new URLSearchParams(window.location.search);
    const query = urlParams.get('query') || '';
    let currentPage = parseInt(urlParams.get('page')) || 1;

    if (query) {
        searchQuery.value = query;
        fetchResults();
    }

    // Search form submission
    searchForm.addEventListener('submit', function (e) {
        e.preventDefault();
        currentPage = 1;
        updateUrlAndFetch();
    });

    // Filter change handlers
    examFilter.addEventListener('change', function () {
        const examId = this.value;
        selectedExams = examId ? [examId] : [];

        // Reset dependent filters
        subjectFilter.innerHTML = '<option value="">Select Subject</option>';
        chapterFilter.innerHTML = '<option value="">Select Chapter</option>';
        paperFilter.innerHTML = '<option value="">Select Paper</option>';
        selectedSubjects = [];
        selectedChapters = [];
        selectedPapers = [];

        if (examId) {
            // Enable subjects and fetch papers
            subjectFilter.disabled = false;
            paperFilter.disabled = false;

            // Load subjects for this exam
            loadSubjects(examId);

            // Load papers for this exam
            fetchFilters(examId, '', 'paper');
        } else {
            subjectFilter.disabled = true;
            chapterFilter.disabled = true;
            paperFilter.disabled = true;
        }

        currentPage = 1;
        updateUrlAndFetch();
    });

    subjectFilter.addEventListener('change', function () {
        const subjectId = this.value;
        selectedSubjects = subjectId ? [subjectId] : [];

        // Reset chapter filter
        chapterFilter.innerHTML = '<option value="">Select Chapter</option>';
        selectedChapters = [];

        if (subjectId && selectedExams.length > 0) {
            // Enable chapters and fetch chapters
            chapterFilter.disabled = false;
            fetchFilters(selectedExams[0], subjectId, 'chapter');
        } else {
            chapterFilter.disabled = true;
        }

        currentPage = 1;
        updateUrlAndFetch();
    });

    chapterFilter.addEventListener('change', function () {
        const chapterId = this.value;
        selectedChapters = chapterId ? [chapterId] : [];
        currentPage = 1;
        updateUrlAndFetch();
    });

    paperFilter.addEventListener('change', function () {
        const paperId = this.value;
        selectedPapers = paperId ? [paperId] : [];
        currentPage = 1;
        updateUrlAndFetch();
    }); function loadSubjects(examId) {
        // Hardcoded subjects list for each exam
        const examsData = [
            {
                "_id": "b3b5a8d8-f409-4e01-8fd4-043d3055db5e",
                "name": "JEE Main",
                "subjects": [
                    [
                        "7bc04a29-039c-430d-980d-a066b16efc86",
                        "Physics"
                    ],
                    [
                        "bdcc1b1b-5d9d-465d-a7b8-f9619bb61fe7",
                        "Chemistry"
                    ],
                    [
                        "f1d41a0c-1a71-4994-90f3-4b5d82a6f5f9",
                        "Mathematics"
                    ]
                ]
            },
            {
                "_id": "6d34f7cd-c80e-4a42-8c35-2b167f459c06",
                "name": "JEE Advanced",
                "subjects": [
                    [
                        "f66d8bfb-ba6a-4b3f-adbc-fbf402e39020",
                        "Physics"
                    ],
                    [
                        "17d9f684-251f-4f52-8092-1b54b33b1ed5",
                        "Chemistry"
                    ],
                    [
                        "96b44962-2c79-4a42-87ce-f8b87c9e174a",
                        "Mathematics"
                    ]
                ]
            },
            {
                "_id": "2871e14c-fbcf-4047-9955-e210b0fb742b",
                "name": "NDA",
                "subjects": [
                    [
                        "fb0ed4bb-f01a-41a7-8400-dc89ff53e59f",
                        "Mathematics"
                    ]
                ]
            },
            {
                "_id": "f3e78517-c050-4fea-822b-e43c4d2d3523",
                "name": "WBJEE",
                "subjects": [
                    [
                        "c41e01c9-86c8-41ff-8b48-e585020ec8c9",
                        "Physics"
                    ],
                    [
                        "2d96a490-384b-4984-9356-086b3baf166b",
                        "Chemistry"
                    ],
                    [
                        "168bd1c7-3c23-4d1c-ab40-fcf70bb1fb72",
                        "Mathematics"
                    ]
                ]
            },
            {
                "_id": "c8da26c7-cf1b-421f-829b-c95dbdd3cc6a",
                "name": "BITSAT",
                "subjects": [
                    [
                        "45363e06-86a7-4d8e-be8d-318ee79af980",
                        "Physics"
                    ],
                    [
                        "416dff44-e43b-4cd3-8c5a-d30b56d24151",
                        "Chemistry"
                    ],
                    [
                        "6848df90-e6d7-4505-a691-53956ebf45a2",
                        "Mathematics"
                    ]
                ]
            },
            {
                "_id": "4fe0bca2-d3eb-43e8-b705-f4eb7301a74c",
                "name": "VITEEE",
                "subjects": [
                    [
                        "fdd0de52-3277-408a-aed9-12c735635134",
                        "Physics"
                    ],
                    [
                        "2a6d5d09-a157-43a4-aa81-022f2e70f596",
                        "Chemistry"
                    ],
                    [
                        "c476840a-2596-4510-878c-d641b83469dc",
                        "Mathematics"
                    ]
                ]
            },
            {
                "_id": "1aa38a2b-dee5-453e-a394-29c033c16789",
                "name": "MHT CET",
                "subjects": [
                    [
                        "eaccceff-1c6e-4d73-bab0-6b2a2a0fb0a0",
                        "Physics"
                    ],
                    [
                        "fe61bc1d-8b3b-4ce8-ab28-a156c8a62fb8",
                        "Chemistry"
                    ],
                    [
                        "2d820cff-7252-4a17-9f44-10b92970705e",
                        "Mathematics"
                    ]
                ]
            },
            {
                "_id": "bb792041-50de-4cfe-83f3-f899a79c0930",
                "name": "COMEDK",
                "subjects": [
                    [
                        "1ff8290a-8193-4001-a93e-8aa8fcb1f3ac",
                        "Physics"
                    ],
                    [
                        "6ec16a3d-177a-44f3-b342-4c51cf2b1045",
                        "Chemistry"
                    ],
                    [
                        "3d7d5653-4382-4275-be29-58b0eea9f510",
                        "Mathematics"
                    ]
                ]
            },
            {
                "_id": "4625ad6f-33db-4c22-96e0-6c23830482de",
                "name": "NEET",
                "subjects": [
                    [
                        "4b89e781-8987-47aa-84b6-d95025d590b0",
                        "Physics"
                    ],
                    [
                        "45966dd6-eaed-452f-bfcc-e9632c72da0f",
                        "Chemistry"
                    ],
                    [
                        "634d1a76-ecfd-4d2b-bdb9-5d6658948236",
                        "Biology"
                    ]
                ]
            }
        ];

        let options = '<option value="">Select Subject</option>';
        const examData = examsData.find(exam => exam._id === examId);

        if (examData && examData.subjects) {
            examData.subjects.forEach(subject => {
                options += `<option value="${subject[0]}">${subject[1]}</option>`;
            });
        }

        subjectFilter.innerHTML = options;
    }

    function fetchFilters(examId, subjectId = '', type = 'paper') {
        const filterSelect = type === 'paper' ? paperFilter : chapterFilter;

        // Show loading state
        filterSelect.innerHTML = '<option value="">Loading...</option>';

        let url = `/search/filters?examId=${examId}`;
        if (subjectId) {
            url += `&subjectId=${subjectId}`;
        }

        fetch(url)
            .then(response => response.json())
            .then(data => {
                if (Array.isArray(data)) {
                    let options = `<option value="">Select ${type === 'paper' ? 'Paper' : 'Chapter'}</option>`;
                    data.forEach(item => {
                        options += `<option value="${item._id}">${item.name}</option>`;
                    });
                    filterSelect.innerHTML = options;
                } else {
                    filterSelect.innerHTML = `<option value="">No ${type === 'paper' ? 'papers' : 'chapters'} found</option>`;
                }
            })
            .catch(error => {
                console.error(`Error fetching ${type}s:`, error);
                filterSelect.innerHTML = `<option value="">Error loading ${type}s</option>`;
            });
    }
    function updateUrlAndFetch() {
        // Update URL with current parameters
        const url = new URL(window.location);

        const query = searchQuery.value.trim();
        if (query) {
            url.searchParams.set('query', query);
        } else {
            url.searchParams.delete('query');
        }

        url.searchParams.set('page', currentPage);
        window.history.pushState({}, '', url);

        console.log('Fetching page:', currentPage);

        // Fetch results with current parameters
        fetchResults();
    }

    function fetchResults() {
        // Show loading state
        searchResults.innerHTML = `
                <div class="loading-indicator">
                    <div class="spinner"></div>
                    <p>Loading results...</p>
                </div>
            `;

        // Build API URL with filters
        const query = searchQuery.value.trim();

        let apiUrl = `/api/search?page=${currentPage}&limit=10`;

        if (query) {
            apiUrl += `&query=${encodeURIComponent(query)}`;
        }

        if (selectedExams.length > 0) {
            apiUrl += `&examIds=${selectedExams.join(',')}`;
        }

        if (selectedSubjects.length > 0) {
            apiUrl += `&subjectIds=${selectedSubjects.join(',')}`;
        }

        if (selectedChapters.length > 0) {
            apiUrl += `&chapterIds=${selectedChapters.join(',')}`;
        }

        if (selectedPapers.length > 0) {
            apiUrl += `&paperIds=${selectedPapers.join(',')}`;
        }

        // Fetch results from API
        fetch(apiUrl)
            .then(response => response.json())
            .then(data => {

                if (!data.error) {
                    displayResults(data);
                    createPagination(data.pagination);
                } else {
                    searchResults.innerHTML = `<div class="no-results">${data.error}</div>`;
                    paginationContainer.innerHTML = '';
                }
            })
            .catch(error => {
                console.error('Error fetching search results:', error);
                searchResults.innerHTML = '<div class="no-results">An error occurred while fetching results</div>';
                paginationContainer.innerHTML = '';
            });
    }
    function displayResults(data) {
        if (!data.results || data.results.length === 0) {
            searchResults.innerHTML = '<div class="no-results">No results found matching your query</div>';
            return;
        }

        let resultsHTML = '';
        data.results.forEach(question => {                // Determine question level class
            let levelClass = '';
            let levelText = 'Medium';

            if (question.level) {
                const level = question.level;
                if (level === 1) {
                    levelClass = 'level-easy';
                    levelText = 'Easy';
                } else if (level === 3) {
                    levelClass = 'level-hard';
                    levelText = 'Hard';
                } else {
                    levelClass = 'level-medium';
                    levelText = 'Medium';
                }
            }

            // Process question text to handle images properly
            let questionText = question.question;

            // Check if the question contains image tags
            if (questionText.includes('<img')) {
                // Add a special class to ensure images display properly
                questionText = questionText.replace(/<img/g, '<br><img class="question-image"');
            }

            resultsHTML += `
                    <a href="/question/${question._id}" class="question-card-link">
                        <div class="question-card">
                            <div class="question-title">${questionText}</div>
                            <span class="question-level ${levelClass}">${levelText}</span>
                            <div class="question-meta">
                                ${question.exam_name ? `
                                <div class="meta-item">
                                    <i class="fas fa-graduation-cap"></i> ${question.exam_name}
                                </div>` : ''}
                                
                                ${question.subject_name ? `
                                <div class="meta-item">
                                    <i class="fas fa-book"></i> ${question.subject_name}
                                </div>` : ''}
                                
                                ${question.chapter_name ? `
                                <div class="meta-item">
                                    <i class="fas fa-bookmark"></i> ${question.chapter_name}
                                </div>` : ''}
                                
                                ${question.paper_name ? `
                                <div class="meta-item">
                                    <i class="fas fa-file-alt"></i> ${question.paper_name}
                                </div>` : ''}
                                
                                <div class="meta-item">
                                    <i class="fas fa-layer-group"></i> ${question.type || 'MCQ'}
                                </div>
                            </div>
                        </div>
                    </a>
                `;
        });

        searchResults.innerHTML = resultsHTML;

        // Typeset the math after the content is loaded
        if (window.MathJax) {
            MathJax.typesetPromise && MathJax.typesetPromise().catch(err => console.error('MathJax error:', err));
        }
    } function createPagination(paginationData) {
        if (!paginationData || !paginationData.totalPages || paginationData.totalPages <= 1) {
            paginationContainer.innerHTML = '';
            return;
        }

        // Ensure we have numbers for all these values
        const currentPageNum = parseInt(paginationData.currentPage) || 1;
        const totalPages = parseInt(paginationData.totalPages) || 1;
        const totalResults = parseInt(paginationData.totalResults) || 0;
        const limit = parseInt(paginationData.limit) || 10;

        let paginationHTML = `
                <div class="pagination-info">
                    Showing ${Math.min((currentPageNum - 1) * limit + 1, totalResults)} to ${Math.min(currentPageNum * limit, totalResults)} 
                    of ${totalResults} results
                </div>
                <ul class="pagination">
            `;

        // Previous button
        if (currentPageNum > 1) {
            paginationHTML += `
                    <li class="pagination-item prev-page pagination-nav">
                        <i class="fas fa-chevron-left"></i>
                    </li>
                `;
        }

        // Calculate range of pages to show
        let startPage = Math.max(1, currentPageNum - 2);
        let endPage = Math.min(totalPages, startPage + 4);

        // Adjust if we're near the end to always show 5 pages if possible
        if (endPage - startPage < 4 && totalPages > 5) {
            startPage = Math.max(1, totalPages - 4);
        }

        // Generate page numbers
        for (let i = startPage; i <= endPage; i++) {
            paginationHTML += `
                    <li class="pagination-item ${i === currentPageNum ? 'active' : ''}" data-page="${i}">
                        ${i}
                    </li>
                `;
        }

        // Next button
        if (currentPageNum < totalPages) {
            paginationHTML += `
                    <li class="pagination-item next-page pagination-nav">
                        <i class="fas fa-chevron-right"></i>
                    </li>
                `;
        }

        paginationHTML += `</ul>`;
        paginationContainer.innerHTML = paginationHTML;

        // Add event listeners to pagination items
        document.querySelectorAll('.pagination-item').forEach(item => {
            item.addEventListener('click', function () {
                let newPage;

                if (this.classList.contains('prev-page')) {
                    newPage = currentPageNum - 1;
                } else if (this.classList.contains('next-page')) {
                    newPage = currentPageNum + 1;
                } else {
                    newPage = parseInt(this.getAttribute('data-page'));
                }

                // Update the global currentPage variable
                currentPage = newPage;

                // Update URL and fetch new results
                updateUrlAndFetch();

                // Scroll back to top of results
                window.scrollTo({
                    top: searchForm.offsetTop - 20,
                    behavior: 'smooth'
                });
            });
        });
    }
});