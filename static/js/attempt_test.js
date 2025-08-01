// Test Attempt JavaScript

// Store test state
const testState = {
    currentQuestion: 0,
    currentSubject: testData.subjects[0]?.id,
    questions: [],
    answers: {},
    marked: {},
    timer: {
        startTime: Date.now(),
        duration: testData.duration * 60 * 1000, // Convert minutes to milliseconds
        timeLeft: testData.duration * 60 * 1000,
        interval: null
    }
};

// Elements
const questionContainer = document.getElementById('question-container');
const questionPalette = document.getElementById('question-palette-body');
const markBtn = document.getElementById('mark-btn');
const clearBtn = document.getElementById('clear-btn');
const prevBtn = document.getElementById('prev-btn');
const saveNextBtn = document.getElementById('save-next-btn');
const submitBtn = document.getElementById('submit-test-btn');
const tabsWrapper = document.getElementById('tabs-wrapper');
const timerDisplay = document.getElementById('timer-display');

// Global variables
let currentSubjectIndex = 0;
let currentQuestionIndex = 0;
let userAnswers = {};
let markedQuestions = new Set();
let startTime = Date.now();
let totalTimeSpent = 0;

// Question timing variables
let questionStartTime = Date.now();
let questionTimings = {};
let currentQuestionId = null;
let questionTimerInterval = null;

// Initialize test
function initializeTest() {
    initializeQuestions();
    renderQuestionPalette();
    renderCurrentQuestion();
    setupNavigation();
    
    // Start test timer
    startTestTimer();
    
    // Submit button
    submitBtn.addEventListener('click', openSubmitModal);
    
    // Modal close buttons
    document.getElementById('close-submit-modal').addEventListener('click', () => {
        document.getElementById('submit-modal').style.display = 'none';
    });
    
    document.getElementById('cancel-submit').addEventListener('click', () => {
        document.getElementById('submit-modal').style.display = 'none';
    });
    
    document.getElementById('confirm-submit').addEventListener('click', submitTest);
    
    // Close modal when clicking outside
    window.addEventListener('click', (event) => {
        const modal = document.getElementById('submit-modal');
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });
    
    // Warn before unload
    window.addEventListener('beforeunload', (e) => {
        const confirmationMessage = 'If you leave this page, your progress will be lost. Are you sure?';
        e.returnValue = confirmationMessage;
        return confirmationMessage;
    });
    
    // Keyboard navigation
    window.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowLeft') {
            navigateToQuestion(testState.currentQuestion - 1);
        } else if (e.key === 'ArrowRight') {
            navigateToQuestion(testState.currentQuestion + 1);
        } else if (e.key >= '1' && e.key <= '9') {
            const optionIndex = parseInt(e.key) - 1;
            const question = testState.questions[testState.currentQuestion];
            if (question.type === 'singleCorrect' && optionIndex < question.options.length) {
                selectOption(optionIndex);
            }
        }
    });
}

// Flatten all questions from subjects into a single array for easier navigation
function initializeQuestions() {
    testState.questions = [];
    let questionIndex = 0;
    
    testData.subjects.forEach(subject => {
        subject.questions.forEach(question => {
            testState.questions.push({
                ...question,
                subjectId: subject.id,
                subjectName: subject.name,
                questionIndex: questionIndex++,
                status: 'not-visited'
            });
        });
    });

    // Initialize answers and marked objects
    testState.questions.forEach((question, index) => {
        testState.answers[index] = null;
        testState.marked[index] = false;
    });
}

// Render current question
function renderCurrentQuestion() {
    const question = testState.questions[testState.currentQuestion];
    
    if (!question) {
        console.error('No question found at index', testState.currentQuestion);
        return;
    }
    
    // Record time spent on previous question when switching
    if (currentQuestionId) {
        const timeSpent = Date.now() - questionStartTime;
        questionTimings[currentQuestionId] = (questionTimings[currentQuestionId] || 0) + timeSpent;
    }
    
    // Reset timer for the new question
    questionStartTime = Date.now();
    currentQuestionId = question._id;
    
    // Mark question as visited
    if (question.status === 'not-visited') {
        question.status = 'not-answered';
        renderQuestionPalette();
    }
    
    // Create question HTML
    let questionHTML = `
        <div class="question" data-index="${testState.currentQuestion}">
            <div class="question-header">
                <div class="question-number-display">Question ${testState.currentQuestion + 1} of ${testState.questions.length}</div>
                <div class="question-badges">
                    <span class="question-type-badge">${question.type === 'singleCorrect' ? 'MCQ' : 'Numerical'}</span>
                    <span class="timer-badge" id="timer-badge">00:00</span>
                </div>
            </div>
            <div class="question-text">
                ${question.question}
            </div>
    `;
    
    // Add options for MCQs or numerical input
    if (question.type === 'singleCorrect') {
        questionHTML += `<div class="options-list">`;
        question.options.forEach((option, i) => {
            const isSelected = testState.answers[testState.currentQuestion] === i;
            questionHTML += `
                <div class="option ${isSelected ? 'selected' : ''}" data-option="${i}">
                    <input type="radio" id="option-${i}" name="question-option" class="option-input" ${isSelected ? 'checked' : ''}>
                    <label for="option-${i}" class="option-text">${option}</label>
                </div>
            `;
        });
        questionHTML += `</div>`;
    } else if (question.type === 'numerical') {
        const currentAnswer = testState.answers[testState.currentQuestion] !== null ?
            testState.answers[testState.currentQuestion] : '';
        questionHTML += `
            <div class="numerical-answer">
                <input type="number" step="0.01" class="numerical-input" placeholder="Enter your answer" value="${currentAnswer}">
            </div>
        `;
    }
    
    questionHTML += `</div>`;
    questionContainer.innerHTML = questionHTML;
    
    // Process MathJax
    if (window.MathJax) {
        window.MathJax.typeset();
    }
    
    // Add event listeners for options
    if (question.type === 'singleCorrect') {
        const options = questionContainer.querySelectorAll('.option');
        options.forEach(option => {
            option.addEventListener('click', () => {
                const optionIndex = parseInt(option.getAttribute('data-option'));
                selectOption(optionIndex);
            });
        });
    } else if (question.type === 'numerical') {
        const numericalInput = questionContainer.querySelector('.numerical-input');
        numericalInput.addEventListener('input', (e) => {
            testState.answers[testState.currentQuestion] = e.target.value ? parseFloat(e.target.value) : null;
            updateQuestionStatus(testState.currentQuestion);
        });
    }
    
    // Update mark button text based on current state
    updateMarkButtonText();
    
    // Start timer for the question
    startQuestionTimer();
    
    // Update the timer display immediately
    const prevTime = questionTimings[currentQuestionId] || 0;
    updateTimerDisplay(prevTime);
}

// Start question timer
function startQuestionTimer() {
    // Clear any existing interval
    if (questionTimerInterval) {
        clearInterval(questionTimerInterval);
    }
    
    // Get accumulated time for current question (if any)
    const accumulatedTime = questionTimings[currentQuestionId] || 0;
    
    questionTimerInterval = setInterval(function() {
        // Calculate elapsed time for current question, including any previously accumulated time
        const elapsedTime = Date.now() - questionStartTime;
        const totalTime = accumulatedTime + elapsedTime;
        
        // Update the timer display
        updateTimerDisplay(totalTime);
    }, 1000); // Update every second
}

// Update timer display
function updateTimerDisplay(timeInMs) {
    // Convert to seconds and format
    const totalSeconds = Math.floor(timeInMs / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    const formattedTime = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    
    // Update badge in question header
    const timerBadge = document.getElementById('timer-badge');
    if (timerBadge) {
        timerBadge.textContent = formattedTime;
    }
}

// Start test timer
function startTestTimer() {
    const duration = testData.duration * 60 * 1000; // Convert minutes to milliseconds
    const timerDisplay = document.getElementById('timer-display');
    
    const interval = setInterval(function() {
        const elapsed = Date.now() - startTime;
        const remaining = duration - elapsed;
        
        if (remaining <= 0) {
            clearInterval(interval);
            submitTest(); // Auto-submit when time's up
            return;
        }
        
        const hours = Math.floor(remaining / (1000 * 60 * 60));
        const minutes = Math.floor((remaining % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((remaining % (1000 * 60)) / 1000);
        
        timerDisplay.textContent = 
            `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }, 1000);
}

// Navigate to a specific question
function navigateToQuestion(index) {
    if (index < 0) {
        index = testState.questions.length - 1; // Wrap to last question when going back from first
    } else if (index >= testState.questions.length) {
        index = 0; // Wrap to first question when going forward from last
    }
    
    // Record time spent on current question
    if (currentQuestionId) {
        const timeSpent = Date.now() - questionStartTime;
        questionTimings[currentQuestionId] = (questionTimings[currentQuestionId] || 0) + timeSpent;
    }
    
    testState.currentQuestion = index;
    const newSubjectId = testState.questions[index].subjectId;
    
    // Update current subject if necessary
    if (newSubjectId !== testState.currentSubject) {
        testState.currentSubject = newSubjectId;
        renderSubjectTabs();
    }
    
    renderCurrentQuestion();
    renderQuestionPalette();
}

// Submit test
function submitTest() {
    // Record time for the current question
    if (currentQuestionId) {
        const timeSpent = Date.now() - questionStartTime;
        questionTimings[currentQuestionId] = (questionTimings[currentQuestionId] || 0) + timeSpent;
    }
    
    // Stop all timers
    clearInterval(questionTimerInterval);
    
    // Transform answers to the required format
    const formattedAnswers = {};
    testState.questions.forEach((question, index) => {
        if (testState.answers[index] !== null) {
            formattedAnswers[question._id] = testState.answers[index];
        }
    });
    
    // Calculate total time spent
    totalTimeSpent = Date.now() - startTime;
    
    // Prepare submission data
    const submissionData = {
        testId: testData._id,
        answers: formattedAnswers,
        timeSpent: totalTimeSpent,
        questionTimings: questionTimings
    };
    
    // Send submission to server
    fetch('/test/submit', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(submissionData)
    })
    .then(response => response.json())
    .then(data => {
        // Redirect to analysis page
        window.location.href = `/test/${testData._id}/analysis`;
    })
    .catch(error => {
        console.error('Error submitting test:', error);
        alert('There was an error submitting your test. Please try again.');
    });
}

// Render question palette
function renderQuestionPalette() {
    questionPalette.innerHTML = '';
    
    testState.questions.forEach((question, index) => {
        if (question.subjectId === testState.currentSubject) {
            const questionBtn = document.createElement('button');
            questionBtn.className = `question-number ${question.status}`;
            if (index === testState.currentQuestion) {
                questionBtn.classList.add('current');
            }
            questionBtn.textContent = index + 1;
            questionBtn.addEventListener('click', () => navigateToQuestion(index));
            questionPalette.appendChild(questionBtn);
        }
    });
}

// Render subject tabs
function renderSubjectTabs() {
    const tabs = tabsWrapper.querySelectorAll('.subject-tab');
    tabs.forEach(tab => {
        const subjectId = tab.getAttribute('data-subject');
        if (subjectId === testState.currentSubject) {
            tab.classList.add('active');
        } else {
            tab.classList.remove('active');
        }
    });
}

// Update question status
function updateQuestionStatus(index) {
    const question = testState.questions[index];
    const hasAnswer = testState.answers[index] !== null;
    const isMarked = testState.marked[index];
    
    if (hasAnswer && isMarked) {
        question.status = 'answered-and-marked';
    } else if (hasAnswer) {
        question.status = 'answered';
    } else if (isMarked) {
        question.status = 'marked';
    } else if (question.status !== 'not-visited') {
        question.status = 'not-answered';
    }
    
    renderQuestionPalette();
}

// Format time
function formatTime(milliseconds) {
    const totalSeconds = Math.floor(milliseconds / 1000);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    
    return [
        hours.toString().padStart(2, '0'),
        minutes.toString().padStart(2, '0'),
        seconds.toString().padStart(2, '0')
    ].join(':');
}

// Update timer display
function updateTimer() {
    const now = Date.now();
    const elapsed = now - testState.timer.startTime;
    const timeLeft = Math.max(0, testState.timer.duration - elapsed);
    testState.timer.timeLeft = timeLeft;
    
    timerDisplay.textContent = formatTime(timeLeft);
    
    // Warning color when less than 5 minutes
    if (timeLeft < 5 * 60 * 1000) {
        timerDisplay.style.color = 'var(--danger)';
        timerDisplay.parentElement.style.borderColor = 'var(--danger)';
    }
    
    // Auto submit when time is up
    if (timeLeft <= 0) {
        clearInterval(testState.timer.interval);
        submitTest();
    }
}

// Generate test summary
function generateSummary() {
    let answered = 0;
    let notAnswered = 0;
    let marked = 0;
    let notVisited = 0;
    
    testState.questions.forEach((question, index) => {
        if (testState.answers[index] !== null) {
            answered++;
        } else if (question.status === 'not-visited') {
            notVisited++;
        } else {
            notAnswered++;
        }
        
        if (testState.marked[index]) {
            marked++;
        }
    });
    
    return `
        <div class="summary-stats">
            <div class="stat-item">
                <div class="stat-value">${answered}</div>
                <div class="stat-label">Answered</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">${notAnswered}</div>
                <div class="stat-label">Not Answered</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">${marked}</div>
                <div class="stat-label">Marked</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">${notVisited}</div>
                <div class="stat-label">Not Visited</div>
            </div>
        </div>
    `;
}

// Open submit modal
function openSubmitModal() {
    const submitModal = document.getElementById('submit-modal');
    const submitSummary = document.getElementById('submit-summary');
    
    submitSummary.innerHTML = generateSummary();
    submitModal.style.display = 'block';
}

// Submit test
function submitTest() {
    // Record time for the current question
    if (currentQuestionId) {
        const timeSpent = Date.now() - questionStartTime;
        questionTimings[currentQuestionId] = (questionTimings[currentQuestionId] || 0) + timeSpent;
    }
    
    // Stop all timers
    clearInterval(questionTimerInterval);
    
    // Transform answers to the required format
    const formattedAnswers = {};
    testState.questions.forEach((question, index) => {
        if (testState.answers[index] !== null) {
            formattedAnswers[question._id] = testState.answers[index];
        }
    });
    
    // Calculate total time spent
    totalTimeSpent = Date.now() - startTime;
    
    // Prepare submission data
    const submissionData = {
        testId: testData._id,
        answers: formattedAnswers,
        timeSpent: totalTimeSpent,
        questionTimings: questionTimings
    };
    
    // Send submission to server
    fetch('/test/submit', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(submissionData)
    })
    .then(response => response.json())
    .then(data => {
        // Redirect to analysis page
        window.location.href = `/test/${testData._id}/analysis`;
    })
    .catch(error => {
        console.error('Error submitting test:', error);
        alert('There was an error submitting your test. Please try again.');
    });
}

// Render question palette
function renderQuestionPalette() {
    questionPalette.innerHTML = '';
    
    testState.questions.forEach((question, index) => {
        if (question.subjectId === testState.currentSubject) {
            const questionBtn = document.createElement('button');
            questionBtn.className = `question-number ${question.status}`;
            if (index === testState.currentQuestion) {
                questionBtn.classList.add('current');
            }
            questionBtn.textContent = index + 1;
            questionBtn.addEventListener('click', () => navigateToQuestion(index));
            questionPalette.appendChild(questionBtn);
        }
    });
}

// Render subject tabs
function renderSubjectTabs() {
    const tabs = tabsWrapper.querySelectorAll('.subject-tab');
    tabs.forEach(tab => {
        const subjectId = tab.getAttribute('data-subject');
        if (subjectId === testState.currentSubject) {
            tab.classList.add('active');
        } else {
            tab.classList.remove('active');
        }
    });
}

// Update question status
function updateQuestionStatus(index) {
    const question = testState.questions[index];
    const hasAnswer = testState.answers[index] !== null;
    const isMarked = testState.marked[index];
    
    if (hasAnswer && isMarked) {
        question.status = 'answered-and-marked';
    } else if (hasAnswer) {
        question.status = 'answered';
    } else if (isMarked) {
        question.status = 'marked';
    } else if (question.status !== 'not-visited') {
        question.status = 'not-answered';
    }
    
    renderQuestionPalette();
}

// Select an option for MCQ
function selectOption(optionIndex) {
    testState.answers[testState.currentQuestion] = optionIndex;
    
    const options = questionContainer.querySelectorAll('.option');
    options.forEach((option, i) => {
        const radio = option.querySelector('input[type="radio"]');
        if (i === optionIndex) {
            option.classList.add('selected');
            radio.checked = true;
        } else {
            option.classList.remove('selected');
            radio.checked = false;
        }
    });
    
    updateQuestionStatus(testState.currentQuestion);
}

// Clear response for current question
function clearResponse() {
    testState.answers[testState.currentQuestion] = null;
    
    const question = testState.questions[testState.currentQuestion];
    if (question.type === 'singleCorrect') {
        const options = questionContainer.querySelectorAll('.option');
        options.forEach(option => {
            option.classList.remove('selected');
            const radio = option.querySelector('input[type="radio"]');
            radio.checked = false;
        });
    } else if (question.type === 'numerical') {
        const numericalInput = questionContainer.querySelector('.numerical-input');
        numericalInput.value = '';
    }
    
    updateQuestionStatus(testState.currentQuestion);
}

// Toggle mark status for current question
function toggleMarkForReview() {
    testState.marked[testState.currentQuestion] = !testState.marked[testState.currentQuestion];
    updateQuestionStatus(testState.currentQuestion);
    updateMarkButtonText();
}

// Update mark button text based on current state
function updateMarkButtonText() {
    markBtn.innerHTML = testState.marked[testState.currentQuestion]
        ? `<i class="fas fa-flag-checkered"></i> Unmark`
        : `<i class="fas fa-flag"></i> Mark for Review`;
}

// Navigate to specific question
function navigateToQuestion(index) {
    if (index < 0) {
        index = testState.questions.length - 1; // Wrap to last question when going back from first
    } else if (index >= testState.questions.length) {
        index = 0; // Wrap to first question when going forward from last
    }
    
    // Record time spent on current question
    if (currentQuestionId) {
        const timeSpent = Date.now() - questionStartTime;
        questionTimings[currentQuestionId] = (questionTimings[currentQuestionId] || 0) + timeSpent;
    }
    
    testState.currentQuestion = index;
    const newSubjectId = testState.questions[index].subjectId;
    
    // Update current subject if necessary
    if (newSubjectId !== testState.currentSubject) {
        testState.currentSubject = newSubjectId;
        renderSubjectTabs();
    }
    
    renderCurrentQuestion();
    renderQuestionPalette();
    
    // Set focus back to the question container for accessibility
    questionContainer.focus();
}

// Handle navigation buttons
function setupNavigation() {
    // Remove existing event listeners first to prevent duplicates
    prevBtn.removeEventListener('click', navigateToPrev);
    saveNextBtn.removeEventListener('click', navigateToNext);
    
    // Add event listeners with named functions for easier debugging
    prevBtn.addEventListener('click', navigateToPrev);
    saveNextBtn.addEventListener('click', navigateToNext);
    
    markBtn.addEventListener('click', toggleMarkForReview);
    clearBtn.addEventListener('click', clearResponse);
    
    // Subject tab navigation
    const subjectTabs = document.querySelectorAll('.subject-tab');
    subjectTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const subjectId = tab.getAttribute('data-subject');
            testState.currentSubject = subjectId;
            
            // Find first question of this subject
            const firstQuestionIndex = testState.questions.findIndex(q => q.subjectId === subjectId);
            if (firstQuestionIndex !== -1) {
                navigateToQuestion(firstQuestionIndex);
            }
            
            renderSubjectTabs();
            renderQuestionPalette();
        });
    });
    
    // Tab scroll buttons
    const scrollLeftBtn = document.getElementById('scroll-left');
    const scrollRightBtn = document.getElementById('scroll-right');
    
    scrollLeftBtn.addEventListener('click', () => {
        tabsWrapper.scrollBy({ left: -200, behavior: 'smooth' });
    });
    
    scrollRightBtn.addEventListener('click', () => {
        tabsWrapper.scrollBy({ left: 200, behavior: 'smooth' });
    });
}

// Navigation handler functions
function navigateToPrev() {
    navigateToQuestion(testState.currentQuestion - 1);
}

function navigateToNext() {
    navigateToQuestion(testState.currentQuestion + 1);
}

// Initialize when the DOM is loaded
document.addEventListener('DOMContentLoaded', initializeTest);

// Render question palette
function renderQuestionPalette() {
    questionPalette.innerHTML = '';
    
    testState.questions.forEach((question, index) => {
        if (question.subjectId === testState.currentSubject) {
            const questionBtn = document.createElement('button');
            questionBtn.className = `question-number ${question.status}`;
            if (index === testState.currentQuestion) {
                questionBtn.classList.add('current');
            }
            questionBtn.textContent = index + 1;
            questionBtn.addEventListener('click', () => navigateToQuestion(index));
            questionPalette.appendChild(questionBtn);
        }
    });
}

// Render subject tabs
function renderSubjectTabs() {
    const tabs = tabsWrapper.querySelectorAll('.subject-tab');
    tabs.forEach(tab => {
        const subjectId = tab.getAttribute('data-subject');
        if (subjectId === testState.currentSubject) {
            tab.classList.add('active');
        } else {
            tab.classList.remove('active');
        }
    });
}

// Update question status
function updateQuestionStatus(index) {
    const question = testState.questions[index];
    const hasAnswer = testState.answers[index] !== null;
    const isMarked = testState.marked[index];
    
    if (hasAnswer && isMarked) {
        question.status = 'answered-and-marked';
    } else if (hasAnswer) {
        question.status = 'answered';
    } else if (isMarked) {
        question.status = 'marked';
    } else if (question.status !== 'not-visited') {
        question.status = 'not-answered';
    }
    
    renderQuestionPalette();
}

// Select an option for MCQ
function selectOption(optionIndex) {
    testState.answers[testState.currentQuestion] = optionIndex;
    
    const options = questionContainer.querySelectorAll('.option');
    options.forEach((option, i) => {
        const radio = option.querySelector('input[type="radio"]');
        if (i === optionIndex) {
            option.classList.add('selected');
            radio.checked = true;
        } else {
            option.classList.remove('selected');
            radio.checked = false;
        }
    });
    
    updateQuestionStatus(testState.currentQuestion);
}

// Clear response for current question
function clearResponse() {
    testState.answers[testState.currentQuestion] = null;
    
    const question = testState.questions[testState.currentQuestion];
    if (question.type === 'singleCorrect') {
        const options = questionContainer.querySelectorAll('.option');
        options.forEach(option => {
            option.classList.remove('selected');
            const radio = option.querySelector('input[type="radio"]');
            radio.checked = false;
        });
    } else if (question.type === 'numerical') {
        const numericalInput = questionContainer.querySelector('.numerical-input');
        numericalInput.value = '';
    }
    
    updateQuestionStatus(testState.currentQuestion);
}

// Toggle mark status for current question
function toggleMarkForReview() {
    testState.marked[testState.currentQuestion] = !testState.marked[testState.currentQuestion];
    updateQuestionStatus(testState.currentQuestion);
    updateMarkButtonText();
}

// Update mark button text based on current state
function updateMarkButtonText() {
    markBtn.innerHTML = testState.marked[testState.currentQuestion]
        ? `<i class="fas fa-flag-checkered"></i> Unmark`
        : `<i class="fas fa-flag"></i> Mark for Review`;
}

// Navigate to specific question
function navigateToQuestion(index) {
    if (index < 0) {
        index = testState.questions.length - 1; // Wrap to last question when going back from first
    } else if (index >= testState.questions.length) {
        index = 0; // Wrap to first question when going forward from last
    }
    
    // Record time spent on current question
    if (currentQuestionId) {
        const timeSpent = Date.now() - questionStartTime;
        questionTimings[currentQuestionId] = (questionTimings[currentQuestionId] || 0) + timeSpent;
    }
    
    testState.currentQuestion = index;
    const newSubjectId = testState.questions[index].subjectId;
    
    // Update current subject if necessary
    if (newSubjectId !== testState.currentSubject) {
        testState.currentSubject = newSubjectId;
        renderSubjectTabs();
    }
    
    renderCurrentQuestion();
    renderQuestionPalette();
    
    // Set focus back to the question container for accessibility
    questionContainer.focus();
}

// Handle navigation buttons
function setupNavigation() {
    prevBtn.addEventListener('click', () => {
        navigateToQuestion(testState.currentQuestion - 1);
    });
    
    saveNextBtn.addEventListener('click', () => {
        navigateToQuestion(testState.currentQuestion + 1);
    });
    
    markBtn.addEventListener('click', toggleMarkForReview);
    clearBtn.addEventListener('click', clearResponse);
    
    // Subject tab navigation
    const subjectTabs = document.querySelectorAll('.subject-tab');
    subjectTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const subjectId = tab.getAttribute('data-subject');
            testState.currentSubject = subjectId;
            
            // Find first question of this subject
            const firstQuestionIndex = testState.questions.findIndex(q => q.subjectId === subjectId);
            if (firstQuestionIndex !== -1) {
                navigateToQuestion(firstQuestionIndex);
            }
            
            renderSubjectTabs();
            renderQuestionPalette();
        });
    });
    
    // Tab scroll buttons
    const scrollLeftBtn = document.getElementById('scroll-left');
    const scrollRightBtn = document.getElementById('scroll-right');
    
    scrollLeftBtn.addEventListener('click', () => {
        tabsWrapper.scrollBy({ left: -200, behavior: 'smooth' });
    });
    
    scrollRightBtn.addEventListener('click', () => {
        tabsWrapper.scrollBy({ left: 200, behavior: 'smooth' });
    });
}

// Initialize when the DOM is loaded
document.addEventListener('DOMContentLoaded', initializeTest);
