let full_data = {};
// Show mode selection after exam is chosen, hide chapters-group until mode is selected
document.getElementById('exam').addEventListener('change', function () {
    document.getElementById('mode-group').style.display = '';
    document.getElementById('chapters-group').innerHTML = '';
    document.getElementById('ratio-group').style.display = 'none';
    // Unselect any previously selected mode
    document.querySelectorAll('input[name="mode"]').forEach(r => r.checked = false);

    // Store the selected exam name for later use in the default test name
    const examSelect = document.getElementById('exam');
    if (examSelect.selectedIndex > 0) {
        window.selectedExamName = examSelect.options[examSelect.selectedIndex].text;
    }
});

// When mode is selected, fetch and show subjects/chapters if "generate" is chosen, or handle previous year paper if "previous" is chosen
document.getElementById('mode-group').addEventListener('change', function (event) {
    const examId = document.getElementById('exam').value;
    const mode = document.querySelector('input[name="mode"]:checked').value;
    const chaptersGroup = document.getElementById('chapters-group');
    chaptersGroup.innerHTML = '';
    document.getElementById('ratio-group').style.display = 'none';

    if (mode === 'generate') {
        fetch(`/api/exams/${examId}/subjects?full=true`)
            .then(response => response.json())
            .then(data => {
                full_data = data;
                
                // Create a container for subject cards to maintain consistent width
                const subjectCardsContainer = document.createElement('div');
                subjectCardsContainer.className = 'subject-cards-container';
                chaptersGroup.appendChild(subjectCardsContainer);
                
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
    } else if (mode === 'previous') {
        // Fetch previous year papers for the selected exam
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

                    // Add container for selected paper configuration
                    const selectedPaperConfig = document.createElement('div');
                    selectedPaperConfig.className = 'selected-paper-config';
                    selectedPaperConfig.style.display = 'none';
                    selectedPaperConfig.innerHTML = `
                            <input type="hidden" name="paper_id" id="selected-paper-id">
                            <div class="config-group">
                                <label for="test-name">Test Name:</label>
                                <input type="text" id="test-name" name="test_name" required>
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

                    pyqsContainer.appendChild(selectedPaperConfig);
                    chaptersGroup.appendChild(pyqsContainer);

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
                    chaptersGroup.innerHTML = '<div class="info-message">No previous year papers found for this exam.</div>';
                }
            })
            .catch(error => {
                console.error('Error fetching previous year papers:', error);
                chaptersGroup.innerHTML = '<div class="info-message error-message">Error loading previous year papers. Please try again.</div>';
            });
    }
});

// on clicking any option from the dropdown, add the value of that option to the hidden input field, also append a badge with the name of the chapter below the dropdown
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
        const badge = document.createElement('span');
        badge.className = 'badge';
        badge.textContent = selectedText;

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
        if (![...selectedChaptersDiv.children].some(b => b.dataset.value === selectedValue)) {
            badge.dataset.value = selectedValue;
            selectedChaptersDiv.appendChild(badge);
        }
    }
});

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
    }

    // Handle Add All and Remove All buttons
    if (event.target.classList.contains('add-all-btn')) {
        const subjectId = event.target.getAttribute('data-subject-id');
        const chaptersSelect = document.querySelector(`.chapters-select[data-subject-id="${subjectId}"]`);
        const hiddenInput = document.querySelector(`input[name="subject-${subjectId}"]`);
        const selectedChaptersDiv = document.getElementById(`selected-chapters-${subjectId}`);
        let allValues = [];
        // Add all options except the first (placeholder)
        for (let i = 1; i < chaptersSelect.options.length; i++) {
            const option = chaptersSelect.options[i];
            allValues.push(option.value);
            // Prevent duplicate badges
            if (![...selectedChaptersDiv.children].some(b => b.dataset.value === option.value)) {
                const badge = document.createElement('span');
                badge.className = 'badge';
                badge.textContent = option.textContent;
                const cross = document.createElement('span');
                cross.className = 'badge-cross';
                cross.innerHTML = '&times;';
                cross.style.marginLeft = '8px';
                cross.style.cursor = 'pointer';
                badge.appendChild(cross);
                badge.dataset.value = option.value;
                selectedChaptersDiv.appendChild(badge);
            }
        }
        hiddenInput.value = "all"; // Indicate all chapters are selected
    }
    if (event.target.classList.contains('remove-all-btn')) {
        const subjectId = event.target.getAttribute('data-subject-id');
        const selectedChaptersDiv = document.getElementById(`selected-chapters-${subjectId}`);
        const hiddenInput = document.querySelector(`input[name="subject-${subjectId}"]`);
        selectedChaptersDiv.innerHTML = '';
        hiddenInput.value = '';
    }

    // Remove/replace the fetch monkey-patch, as we now fetch only on mode selection
    // ...no fetch override needed...
});

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

// Function to generate a formatted date-time string in DD:MM:YYYY HH:mm:SS format
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
    if (window.selectedExamName) {
        const defaultName = `${window.selectedExamName} Test - ${getFormattedDateTime()}`;
        testNameInput.value = defaultName;
        testNameInput.setAttribute('placeholder', defaultName);
    }
}

// Show ratio selector when chapters are selected
document.getElementById('chapters-group').addEventListener('change', function (event) {
    if (event.target.classList.contains('chapters-select')) {
        // ...existing code for badge creation...

        // Show ratio selector if any chapters are selected
        if (checkForSelectedChapters()) {
            document.getElementById('ratio-group').style.display = '';
            setDefaultTestName(); // Set default name when ratio section appears
        }
    }
});

// Update ratio display when slider changes
document.getElementById('ratio-slider').addEventListener('input', function () {
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

// Initialize question count breakdown on page load
document.addEventListener('DOMContentLoaded', function() {
    // Set initial slider fill width to match default value
    const initialMcqPercentage = 80; // Default to 80%
    document.querySelector('.slider-fill').style.width = initialMcqPercentage + '%';
    
    // Initialize the question breakdown after a short delay to ensure elements are ready
    setTimeout(updateQuestionCountBreakdown, 100);
});

// Function to update the question count breakdown based on ratio and total
function updateQuestionCountBreakdown() {
    const totalQuestions = parseInt(document.getElementById('question-count').value) || 75; // Default to 75
    const mcqPercentage = parseInt(document.getElementById('ratio-slider').value) || 80; // Default to 80%
    
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

// Question count increment/decrement buttons
document.getElementById('increase-count').addEventListener('click', function() {
    const countInput = document.getElementById('question-count');
    const currentValue = parseInt(countInput.value) || 30;
    countInput.value = Math.min(currentValue + 5, 100); // Increment by 5, max 100
    updateQuestionCountBreakdown();
});

document.getElementById('decrease-count').addEventListener('click', function() {
    const countInput = document.getElementById('question-count');
    const currentValue = parseInt(countInput.value) || 30;
    countInput.value = Math.max(currentValue - 5, 5); // Decrement by 5, min 5
    updateQuestionCountBreakdown();
});

// Update question count breakdown when count changes directly
document.getElementById('question-count').addEventListener('change', function() {
    const value = parseInt(this.value) || 30;
    this.value = Math.max(5, Math.min(100, value)); // Clamp between 5 and 100
    updateQuestionCountBreakdown();
});

// Duration increment/decrement buttons
document.getElementById('increase-duration').addEventListener('click', function () {
    const durationInput = document.getElementById('test-duration');
    const currentValue = parseInt(durationInput.value) || 180;
    durationInput.value = Math.min(currentValue + 30, 360); // Increment by 30 mins, max 6 hours
});

document.getElementById('decrease-duration').addEventListener('click', function () {
    const durationInput = document.getElementById('test-duration');
    const currentValue = parseInt(durationInput.value) || 180;
    durationInput.value = Math.max(currentValue - 30, 10); // Decrement by 30 mins, min 10 mins
});

// Validate duration on direct input
document.getElementById('test-duration').addEventListener('change', function () {
    const value = parseInt(this.value) || 180;
    this.value = Math.max(10, Math.min(360, value)); // Clamp between 10 and 360
});

// Also check for chapters selection when Add All or Remove All is clicked
document.getElementById('chapters-group').addEventListener('click', function (event) {
    if (event.target.classList.contains('badge-cross')) {
        // ...existing code for removing badge...

        // Hide ratio selector if no chapters are selected
        if (!checkForSelectedChapters()) {
            document.getElementById('ratio-group').style.display = 'none';
        }
    }

    if (event.target.classList.contains('add-all-btn')) {
        // ...existing code for adding all...

        // Show ratio selector since chapters are selected
        document.getElementById('ratio-group').style.display = '';
        setDefaultTestName(); // Set default name when ratio section appears
    }

    if (event.target.classList.contains('remove-all-btn')) {
        // ...existing code for removing all...

        // Check if any other subjects have selections
        if (!checkForSelectedChapters()) {
            document.getElementById('ratio-group').style.display = 'none';
        }
    }
});

// Also update the default test name if it hasn't been modified by the user
const testNameInput = document.getElementById('test-name');
testNameInput.addEventListener('focus', function () {
    if (!this.value) {
        setDefaultTestName();
    }
});

// Duration controls setup function
function setupDurationControls() {
    // Increase button
    document.getElementById('increase-duration').addEventListener('click', function () {
        const durationInput = document.getElementById('test-duration');
        const currentValue = parseInt(durationInput.value) || 180;
        durationInput.value = Math.min(currentValue + 30, 360); // Increment by 30 mins, max 6 hours
    });

    // Decrease button
    document.getElementById('decrease-duration').addEventListener('click', function () {
        const durationInput = document.getElementById('test-duration');
        const currentValue = parseInt(durationInput.value) || 180;
        durationInput.value = Math.max(currentValue - 30, 10); // Decrement by 30 mins, min 10 mins
    });

    // Validate direct input
    document.getElementById('test-duration').addEventListener('change', function () {
        const value = parseInt(this.value) || 180;
        this.value = Math.max(10, Math.min(360, value)); // Clamp between 10 and 360
    });
}

// Helper function to create a paper card
function createPaperCard(paper) {
    const paperCard = document.createElement('div');
    paperCard.className = 'paper-card';
    paperCard.dataset.paperId = paper._id;

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
            const paperName = paperCard.querySelector('h4').textContent;

            // Update all cards to remove selection
            document.querySelectorAll('.paper-card').forEach(card => {
                card.classList.remove('selected');
            });

            // Mark this card as selected
            paperCard.classList.add('selected');

            // Update hidden input with selected paper ID
            document.getElementById('selected-paper-id').value = paperId;

            // Set default test name based on paper name
            document.getElementById('test-name').value = paperName;

            // Show the configuration section
            document.querySelector('.selected-paper-config').style.display = 'block';

            // Add event listeners for duration controls
            setupDurationControls();
        });
    });
}