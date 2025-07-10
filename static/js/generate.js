let full_data = {};

// Show mode selection after exam is chosen, remove all other UI elements
document.getElementById('exam').addEventListener('change', function () {
    // Clear previous content
    clearUIElements();
    
    // Show mode selection
    const modeGroup = document.getElementById('mode-group');
    modeGroup.style.display = '';
    
    // Unselect any previously selected mode
    document.querySelectorAll('input[name="mode"]').forEach(r => r.checked = false);

    // Store the selected exam name for later use in the default test name
    const examSelect = document.getElementById('exam');
    if (examSelect.selectedIndex > 0) {
        window.selectedExamName = examSelect.options[examSelect.selectedIndex].text;
    }
});

// Function to clear UI elements
function clearUIElements() {
    // Clear chapters group
    const chaptersGroup = document.getElementById('chapters-group');
    chaptersGroup.innerHTML = '';
    
    // Remove ratio group from DOM
    const ratioGroup = document.getElementById('ratio-group');
    if (ratioGroup) {
        ratioGroup.style.display = 'none';
        ratioGroup.innerHTML = ''; // Clear its content
    }
}

// When mode is selected, build appropriate UI
document.getElementById('mode-group').addEventListener('change', function (event) {
    const examId = document.getElementById('exam').value;
    const mode = document.querySelector('input[name="mode"]:checked').value;
    const chaptersGroup = document.getElementById('chapters-group');
    
    // Clear previous content
    clearUIElements();

    if (mode === 'generate') {
        buildGenerateUI(examId, chaptersGroup);
    } else if (mode === 'previous') {
        buildPreviousYearUI(examId, chaptersGroup);
    }
});

// Function to build UI for generating custom test
function buildGenerateUI(examId, container) {
    fetch(`/api/exams/${examId}/subjects?full=true`)
        .then(response => response.json())
        .then(data => {
            full_data = data;
            
            // Create a container for subject cards to maintain consistent width
            const subjectCardsContainer = document.createElement('div');
            subjectCardsContainer.className = 'subject-cards-container';
            container.appendChild(subjectCardsContainer);
            
            data.subjects.forEach(subject => {
                const card = document.createElement('div');
                card.className = 'subject-card';
                card.innerHTML = `
                    <h3>${subject.name}</h3>
                    <div class="chapters-control">
                        <select class="chapters-select" data-subject-id="${subject._id}">
                            <option value="" disabled selected>Select chapters</option>
                        </select>
                        <button type="button" class="add-all-btn" data-subject-id="${subject._id}">Add All</button>
                        <button type="button" class="remove-all-btn" data-subject-id="${subject._id}">Remove All</button>
                    </div>
                    <input type="hidden" name="subject-${subject._id}" value="">
                    <div class="selected-chapters" id="selected-chapters-${subject._id}"></div>
                `;
                subjectCardsContainer.appendChild(card);

                const chaptersSelect = card.querySelector('.chapters-select');
                subject.chapters.forEach(chapter => {
                    const option = document.createElement('option');
                    option.value = chapter[0];
                    option.textContent = chapter[1];
                    chaptersSelect.appendChild(option);
                });
            });
        })
        .catch(error => console.error('Error fetching subjects:', error));
}

// Function to build UI for previous year papers
function buildPreviousYearUI(examId, container) {
    fetch(`/api/exams/${examId}/pyqs`)
        .then(response => response.json())
        .then(data => {
            if (data.pyqs && data.pyqs.length > 0) {
                // Create the UI for selecting a previous year paper
                const pyqsContainer = document.createElement('div');
                pyqsContainer.className = 'pyqs-container';

                const heading = document.createElement('h3');
                heading.className = 'pyqs-heading';
                heading.textContent = 'Select a Previous Year Paper';
                pyqsContainer.appendChild(heading);

                // Add search bar
                const searchContainer = document.createElement('div');
                searchContainer.className = 'pyq-search-container';
                searchContainer.innerHTML = `
                    <div class="pyq-search-bar">
                        <i class="fas fa-search"></i>
                        <input type="text" id="pyq-search" placeholder="Search previous papers...">
                        <button type="button" id="clear-search" class="clear-search-btn" style="display:none;">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    <div class="pyq-search-stats">
                        <span id="paper-count">${data.pyqs.length} papers found</span>
                    </div>
                `;
                pyqsContainer.appendChild(searchContainer);

                const papersList = document.createElement('div');
                papersList.className = 'papers-list';
                papersList.id = 'papers-list';

                // Sort papers by timestamp (newest first)
                data.pyqs.sort((a, b) => b.timestamp - a.timestamp);

                // Store papers for filtering later
                const allPapers = [...data.pyqs];

                data.pyqs.forEach(paper => {
                    const paperCard = createPaperCard(paper);
                    papersList.appendChild(paperCard);
                });

                pyqsContainer.appendChild(papersList);
                container.appendChild(pyqsContainer);

                // Add event listeners to paper select buttons
                setupPaperSelectListeners();

                // Search functionality
                const searchInput = document.getElementById('pyq-search');
                const clearSearch = document.getElementById('clear-search');
                const paperCount = document.getElementById('paper-count');

                searchInput.addEventListener('input', function () {
                    const searchTerm = this.value.toLowerCase().trim();
                    clearSearch.style.display = searchTerm ? 'flex' : 'none';

                    // Filter papers based on search term
                    const filteredPapers = allPapers.filter(paper => {
                        const paperName = paper.name.toLowerCase();
                        // Convert timestamp to readable date for searching
                        const date = new Date(paper.timestamp * 1000);
                        const dateString = date.toLocaleDateString('en-US', {
                            year: 'numeric',
                            month: 'long',
                            day: 'numeric'
                        }).toLowerCase();

                        return paperName.includes(searchTerm) || dateString.includes(searchTerm);
                    });

                    // Update papers list
                    const papersList = document.getElementById('papers-list');
                    papersList.innerHTML = '';

                    if (filteredPapers.length > 0) {
                        filteredPapers.forEach(paper => {
                            const paperCard = createPaperCard(paper);
                            papersList.appendChild(paperCard);
                        });

                        // Update paper count
                        paperCount.textContent = `${filteredPapers.length} papers found`;

                        // Re-establish event listeners for the new cards
                        setupPaperSelectListeners();
                    } else {
                        // No results found
                        papersList.innerHTML = `
                            <div class="no-results">
                                <i class="fas fa-search"></i>
                                <p>No papers found matching "${searchTerm}"</p>
                            </div>
                        `;
                        paperCount.textContent = '0 papers found';
                    }
                });

                clearSearch.addEventListener('click', function () {
                    searchInput.value = '';
                    searchInput.dispatchEvent(new Event('input'));
                    searchInput.focus();
                });

            } else {
                container.innerHTML = '<div class="info-message">No previous year papers found for this exam.</div>';
            }
        })
        .catch(error => {
            console.error('Error fetching previous year papers:', error);
            container.innerHTML = '<div class="info-message error-message">Error loading previous year papers. Please try again.</div>';
        });
}

// Helper function to create a paper card
function createPaperCard(paper) {
    const paperCard = document.createElement('div');
    paperCard.className = 'paper-card';
    paperCard.dataset.paperId = paper._id;
    paperCard.dataset.paperName = paper.name;

    // Format timestamp to readable date
    const date = new Date(paper.timestamp * 1000);
    const formattedDate = date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });

    paperCard.innerHTML = `
        <div class="paper-info">
            <h4>${paper.name}</h4>
            <p class="paper-date">${formattedDate}</p>
        </div>
        <div class="paper-action">
            <button type="button" class="select-paper-btn">Select</button>
        </div>
    `;
    return paperCard;
}

// Setup event listeners for paper selection
function setupPaperSelectListeners() {
    document.querySelectorAll('.select-paper-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            const paperCard = this.closest('.paper-card');
            const paperId = paperCard.dataset.paperId;
            const paperName = paperCard.dataset.paperName;

            // Update all cards to remove selection
            document.querySelectorAll('.paper-card').forEach(card => {
                card.classList.remove('selected');
            });

            // Mark this card as selected
            paperCard.classList.add('selected');

            // Build the configuration UI for the selected paper
            buildSelectedPaperConfigUI(paperId, paperName);
        });
    });
}

// Function to build the configuration UI for selected paper
function buildSelectedPaperConfigUI(paperId, paperName) {
    // Remove any existing config UI
    const existingConfig = document.querySelector('.selected-paper-config');
    if (existingConfig) {
        existingConfig.remove();
    }

    // Create the configuration UI
    const selectedPaperConfig = document.createElement('div');
    selectedPaperConfig.className = 'selected-paper-config';
    
    selectedPaperConfig.innerHTML = `
        <input type="hidden" name="paper_id" id="selected-paper-id" value="${paperId}">
        <div class="config-group">
            <label for="test-name">Test Name:</label>
            <input type="text" id="test-name" name="test_name" value="${paperName}" required>
        </div>
        <div class="config-group">
            <label for="test-duration">Duration (minutes):</label>
            <div class="duration-input">
                <input type="number" id="test-duration" name="duration" min="10" max="360" value="180">
                <div class="duration-controls">
                    <button type="button" class="duration-btn" id="decrease-duration"><i class="fas fa-minus"></i></button>
                    <button type="button" class="duration-btn" id="increase-duration"><i class="fas fa-plus"></i></button>
                </div>
            </div>
        </div>
        <div class="submit-container">
            <button type="submit" class="btn btn-primary">
                <i class="fas fa-play-circle me-2"></i> Start Test
            </button>
        </div>
    `;

    // Append to container
    document.querySelector('.pyqs-container').appendChild(selectedPaperConfig);
    
    // Setup duration controls
    setupDurationControls();
}

// Function to build the ratio selector and test configuration UI
function buildRatioAndConfigUI() {
    // Remove any existing ratio UI
    const existingRatioGroup = document.getElementById('ratio-group');
    existingRatioGroup.innerHTML = '';
    existingRatioGroup.style.display = '';
    
    // Create ratio selector container
    const ratioSelectorContainer = document.createElement('div');
    ratioSelectorContainer.className = 'ratio-selector-container';
    ratioSelectorContainer.innerHTML = `
        <h3 class="ratio-title">Question Type Ratio</h3>
        <div class="ratio-labels">
            <span>Multiple Choice</span>
            <span>Numerical</span>
        </div>
        <div class="slider-container">
            <div class="slider-track">
                <div class="slider-fill"></div>
            </div>
            <input type="range" id="ratio-slider" name="mcq_ratio" min="0" max="100" value="80" class="ratio-slider">
            <div class="slider-markers">
                <span>0%</span>
                <span>25%</span>
                <span>50%</span>
                <span>75%</span>
                <span>100%</span>
            </div>
        </div>
        <div class="ratio-display">
            <div class="ratio-box mcq-box">
                <i class="fas fa-list-ul"></i>
                <span id="mcq-percentage">80%</span>
                <span>MCQ</span>
            </div>
            <div class="ratio-box numerical-box">
                <i class="fas fa-calculator"></i>
                <span id="numerical-percentage">20%</span>
                <span>Numerical</span>
            </div>
        </div>
    `;
    
    // Create test configuration container
    const testConfigContainer = document.createElement('div');
    testConfigContainer.className = 'test-config-container';
    testConfigContainer.innerHTML = `
        <h3 class="config-title">Test Configuration</h3>
        
        <div class="config-group">
            <label for="question-count">Number of Questions:</label>
            <div class="count-input">
                <input type="number" id="question-count" name="question_count" min="5" max="100" value="75">
                <div class="count-controls">
                    <button type="button" class="count-btn" id="decrease-count"><i class="fas fa-minus"></i></button>
                    <button type="button" class="count-btn" id="increase-count"><i class="fas fa-plus"></i></button>
                </div>
            </div>
        </div>
        
        <div class="config-group">
            <label for="test-duration">Duration (minutes):</label>
            <div class="duration-input">
                <input type="number" id="test-duration" name="duration" min="10" max="360" value="180">
                <div class="duration-controls">
                    <button type="button" class="duration-btn" id="decrease-duration"><i class="fas fa-minus"></i></button>
                    <button type="button" class="duration-btn" id="increase-duration"><i class="fas fa-plus"></i></button>
                </div>
            </div>
        </div>
        
        <div class="config-group">
            <label for="test-name">Test Name:</label>
            <input type="text" id="test-name" name="test_name" placeholder="e.g., Physics Mechanics Practice" required>
        </div>
        
        <div class="config-group">
            <label for="test-description">Description (optional):</label>
            <textarea id="test-description" name="description" rows="3" placeholder="Add notes about the focus of this test"></textarea>
        </div>
    `;
    
    // Create submit button container
    const submitContainer = document.createElement('div');
    submitContainer.className = 'submit-container';
    submitContainer.innerHTML = `
        <button type="submit" id="generate-btn" class="btn btn-primary">
            <i class="fas fa-magic me-2"></i> Generate Test
        </button>
    `;
    
    // Append to ratio group
    existingRatioGroup.appendChild(ratioSelectorContainer);
    existingRatioGroup.appendChild(testConfigContainer);
    existingRatioGroup.appendChild(submitContainer);
    
    // Setup event listeners for the new elements
    setupRatioControls();
    setupQuestionCountControls();
    setupDurationControls();
    
    // Set default test name
    setDefaultTestName();
    
    // Initialize slider fill
    document.querySelector('.slider-fill').style.width = '80%';
    
    // Initialize question counts
    updateQuestionCountBreakdown();
}

// Function to check if any chapters are selected
function checkForSelectedChapters() {
    const hiddenInputs = document.querySelectorAll('input[type="hidden"][name^="subject-"]');
    for (const input of hiddenInputs) {
        if (input.value && input.value.length > 0) {
            return true;
        }
    }
    return false;
}

// on clicking any option from the dropdown, add the value of that option to the hidden input field
document.getElementById('chapters-group').addEventListener('change', function (event) {
    if (event.target.classList.contains('chapters-select')) {
        const select = event.target;
        const subjectId = select.getAttribute('data-subject-id');
        const selectedValue = select.value;
        const selectedText = select.options[select.selectedIndex].text;

        // Update hidden input (store as comma-separated list for multiple chapters)
        const hiddenInput = document.querySelector(`input[name="subject-${subjectId}"]`);
        let currentValues = hiddenInput.value ? hiddenInput.value.split(',') : [];
        if (!currentValues.includes(selectedValue)) {
            currentValues.push(selectedValue);
            hiddenInput.value = currentValues.join(',');
        }

        // Create badge with cross icon
        createChapterBadge(subjectId, selectedValue, selectedText);
        
        // Show ratio selector if any chapters are selected
        if (checkForSelectedChapters()) {
            buildRatioAndConfigUI();
        }
    }
});

// Function to create chapter badge
function createChapterBadge(subjectId, value, text) {
    const badge = document.createElement('span');
    badge.className = 'badge';
    badge.textContent = text;
    badge.dataset.value = value;

    // Add cross icon
    const cross = document.createElement('span');
    cross.className = 'badge-cross';
    cross.innerHTML = '&times;';
    cross.style.marginLeft = '8px';
    cross.style.cursor = 'pointer';
    badge.appendChild(cross);

    // Append badge below the select
    const selectedChaptersDiv = document.getElementById(`selected-chapters-${subjectId}`);
    // Prevent duplicate badges
    if (![...selectedChaptersDiv.children].some(b => b.dataset.value === value)) {
        selectedChaptersDiv.appendChild(badge);
    }
}

// Remove badge and update hidden input when cross is clicked
document.getElementById('chapters-group').addEventListener('click', function (event) {
    if (event.target.classList.contains('badge-cross')) {
        const badge = event.target.parentElement;
        const subjectId = badge.parentElement.id.replace('selected-chapters-', '');
        const valueToRemove = badge.dataset.value;
        // Remove badge
        badge.remove();
        // Update hidden input
        const hiddenInput = document.querySelector(`input[name="subject-${subjectId}"]`);
        let currentValues = hiddenInput.value ? hiddenInput.value.split(',') : [];
        currentValues = currentValues.filter(val => val !== valueToRemove);
        hiddenInput.value = currentValues.join(',');
        
        // Hide ratio selector if no chapters are selected
        if (!checkForSelectedChapters()) {
            const ratioGroup = document.getElementById('ratio-group');
            ratioGroup.style.display = 'none';
            ratioGroup.innerHTML = '';
        }
    }

    // Handle Add All and Remove All buttons
    if (event.target.classList.contains('add-all-btn')) {
        const subjectId = event.target.getAttribute('data-subject-id');
        const chaptersSelect = document.querySelector(`.chapters-select[data-subject-id="${subjectId}"]`);
        const hiddenInput = document.querySelector(`input[name="subject-${subjectId}"]`);
        const selectedChaptersDiv = document.getElementById(`selected-chapters-${subjectId}`);
        
        // Clear existing badges
        selectedChaptersDiv.innerHTML = '';
        
        // Add all options except the first (placeholder)
        for (let i = 1; i < chaptersSelect.options.length; i++) {
            const option = chaptersSelect.options[i];
            createChapterBadge(subjectId, option.value, option.textContent);
        }
        
        // Set value to "all" to indicate all chapters are selected
        hiddenInput.value = "all";
        
        // Show ratio selector
        buildRatioAndConfigUI();
    }
    
    if (event.target.classList.contains('remove-all-btn')) {
        const subjectId = event.target.getAttribute('data-subject-id');
        const selectedChaptersDiv = document.getElementById(`selected-chapters-${subjectId}`);
        const hiddenInput = document.querySelector(`input[name="subject-${subjectId}"]`);
        
        // Clear badges and input
        selectedChaptersDiv.innerHTML = '';
        hiddenInput.value = '';
        
        // Hide ratio selector if no chapters are selected
        if (!checkForSelectedChapters()) {
            const ratioGroup = document.getElementById('ratio-group');
            ratioGroup.style.display = 'none';
            ratioGroup.innerHTML = '';
        }
    }
});

// Function to generate a formatted date-time string
function getFormattedDateTime() {
    const now = new Date();
    const day = String(now.getDate()).padStart(2, '0');
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const year = now.getFullYear();
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');

    return `${day}:${month}:${year} ${hours}:${minutes}:${seconds}`;
}

// Function to set the default test name
function setDefaultTestName() {
    const testNameInput = document.getElementById('test-name');
    if (testNameInput && window.selectedExamName) {
        const defaultName = `${window.selectedExamName} Test - ${getFormattedDateTime()}`;
        testNameInput.value = defaultName;
        testNameInput.setAttribute('placeholder', defaultName);
    }
}

// Setup ratio control functions
function setupRatioControls() {
    const ratioSlider = document.getElementById('ratio-slider');
    
    if (ratioSlider) {
        ratioSlider.addEventListener('input', function() {
            const mcqPercentage = this.value;
            const numericalPercentage = 100 - mcqPercentage;
            
            // Update percentage displays
            document.getElementById('mcq-percentage').textContent = mcqPercentage + '%';
            document.getElementById('numerical-percentage').textContent = numericalPercentage + '%';
            
            // Update slider fill
            document.querySelector('.slider-fill').style.width = mcqPercentage + '%';
            
            // Update question count breakdown
            updateQuestionCountBreakdown();
        });
    }
}

// Function to update question count breakdown
function updateQuestionCountBreakdown() {
    const totalQuestions = parseInt(document.getElementById('question-count').value) || 75;
    const mcqPercentage = parseInt(document.getElementById('ratio-slider').value) || 80;
    
    // Calculate counts
    const mcqCount = Math.round(totalQuestions * (mcqPercentage / 100));
    const numericalCount = totalQuestions - mcqCount;
    
    // Update the display if elements exist
    const mcqBox = document.querySelector('.mcq-box');
    const numericalBox = document.querySelector('.numerical-box');
    
    if (mcqBox) {
        // Check if count display exists, create if not
        let mcqCountDisplay = mcqBox.querySelector('.question-count');
        if (!mcqCountDisplay) {
            mcqCountDisplay = document.createElement('div');
            mcqCountDisplay.className = 'question-count';
            mcqBox.appendChild(mcqCountDisplay);
        }
        mcqCountDisplay.textContent = `${mcqCount} questions`;
    }
    
    if (numericalBox) {
        // Check if count display exists, create if not
        let numericalCountDisplay = numericalBox.querySelector('.question-count');
        if (!numericalCountDisplay) {
            numericalCountDisplay = document.createElement('div');
            numericalCountDisplay.className = 'question-count';
            numericalBox.appendChild(numericalCountDisplay);
        }
        numericalCountDisplay.textContent = `${numericalCount} questions`;
    }
}

// Setup question count controls
function setupQuestionCountControls() {
    const increaseCount = document.getElementById('increase-count');
    const decreaseCount = document.getElementById('decrease-count');
    const questionCount = document.getElementById('question-count');
    
    if (increaseCount) {
        increaseCount.addEventListener('click', function() {
            const currentValue = parseInt(questionCount.value) || 75;
            questionCount.value = Math.min(currentValue + 5, 100);
            updateQuestionCountBreakdown();
        });
    }
    
    if (decreaseCount) {
        decreaseCount.addEventListener('click', function() {
            const currentValue = parseInt(questionCount.value) || 75;
            questionCount.value = Math.max(currentValue - 5, 5);
            updateQuestionCountBreakdown();
        });
    }
    
    if (questionCount) {
        questionCount.addEventListener('change', function() {
            const value = parseInt(this.value) || 75;
            this.value = Math.max(5, Math.min(100, value));
            updateQuestionCountBreakdown();
        });
    }
}

// Setup duration controls
function setupDurationControls() {
    const increaseDuration = document.getElementById('increase-duration');
    const decreaseDuration = document.getElementById('decrease-duration');
    const testDuration = document.getElementById('test-duration');
    
    if (increaseDuration) {
        increaseDuration.addEventListener('click', function() {
            const currentValue = parseInt(testDuration.value) || 180;
            testDuration.value = Math.min(currentValue + 30, 360);
        });
    }
    
    if (decreaseDuration) {
        decreaseDuration.addEventListener('click', function() {
            const currentValue = parseInt(testDuration.value) || 180;
            testDuration.value = Math.max(currentValue - 30, 10);
        });
    }
    
    if (testDuration) {
        testDuration.addEventListener('change', function() {
            const value = parseInt(this.value) || 180;
            this.value = Math.max(10, Math.min(360, value));
        });
    }
}