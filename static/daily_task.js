document.addEventListener('DOMContentLoaded', function() {
    // Initialize variables
    console.log("Test data:", testData); // Debugging

    let currentQuestionIndex = 0;
    let currentSubjectId = null;
    let questionStatus = {};
    let userAnswers = {};
    let timeSpent = 0;
    let questionTimings = {};
    let currentQuestionStartTime = Date.now();
    let timerInterval;
    
    // Store question data by ID for easy access
    const questionsById = {};
    const questionsOrder = [];
    
    // Process test data
    function initializeTest() {
        // Create a flat array of all questions from all subjects
        let questionNumber = 1;
        
        for (const subject in testData.questions) {
            currentSubjectId = subject;  // Set first subject as default
            
            for (const questionId of testData.questions[subject]) {
                // The issue is here - question data structure needs to be fixed
                const questionData = testData.question_data[questionId];
                
                // In your case, the question data is stored as an array with one item
                const question = questionData && questionData.length > 0 ? questionData[0] : null;
                
                if (question) {
                    // Copy essential properties to avoid modifying the original
                    const processedQuestion = {
                        _id: question._id,
                        text: question.question,
                        // Support both "mcq" type and "singleCorrect" type
                        type: question.type === 'singleCorrect' ? 'mcq' : (question.type || 'mcq'),
                        options: question.options || [],
                        answer: question.correct_option ? question.correct_option[0] : null,
                        subject: subject,
                        questionNumber: questionNumber++
                    };
                    
                    // For numerical questions
                    if (question.type === 'numerical') {
                        processedQuestion.answer = question.correct_value;
                    }
                    
                    questionsById[questionId] = processedQuestion;
                    questionsOrder.push(questionId);
                    
                    // Initialize status for all questions
                    questionStatus[questionId] = 'not-visited';
                }
            }
        }
        
        console.log("Processed questions:", questionsById);
        updateUI();
    }
    
    // Initialize timer
    function initializeTimer() {
        const duration = testData.duration * 60; // Convert to seconds
        let timer = duration;
        
        timerInterval = setInterval(() => {
            timeSpent++;
            timer--;
            
            if (timer < 0) {
                // Time's up - auto-submit
                clearInterval(timerInterval);
                submitTest();
                return;
            }
            
            updateTimerDisplay(timer);
        }, 1000);
    }
    
    function updateTimerDisplay(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;
        
        const display = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        document.getElementById('timer-display').textContent = display;
    }
    
    // Update UI elements
    function updateUI() {
        loadQuestion(currentQuestionIndex);
        updatePalette();
        updateProgressStats();
        if (window.MathJax) {
            window.MathJax.typeset();
        }
    }
    
    // Load a question by index
    // Fix the loadQuestion function to properly display MCQ options
    function loadQuestion(index) {
        if (index < 0 || index >= questionsOrder.length) {
            return;
        }
        
        // Record time spent on previous question
        const now = Date.now();
        if (currentQuestionIndex !== index && currentQuestionIndex < questionsOrder.length) {
            const prevQuestionId = questionsOrder[currentQuestionIndex];
            const timeOnQuestion = now - currentQuestionStartTime;
            
            if (!questionTimings[prevQuestionId]) {
                questionTimings[prevQuestionId] = 0;
            }
            questionTimings[prevQuestionId] += timeOnQuestion;
        }
        
        currentQuestionStartTime = now;
        currentQuestionIndex = index;
        const questionId = questionsOrder[index];
        const question = questionsById[questionId];
        
        // Update status if this question was not visited before
        if (questionStatus[questionId] === 'not-visited') {
            questionStatus[questionId] = 'not-answered';
        }
        
        const questionContainer = document.getElementById('question-container');
        
        // Clear previous content
        questionContainer.innerHTML = '';
        
        // Create question element
        const questionElement = document.createElement('div');
        questionElement.className = 'question';
        
        // Question number and text
        const questionText = document.createElement('div');
        questionText.className = 'question-text';
        questionText.innerHTML = `<strong>Q${question.questionNumber}.</strong> ${question.text}`;
        questionElement.appendChild(questionText);
        
        // Options
        if (question.type === 'mcq' || question.type === 'singleCorrect') {
            const optionsList = document.createElement('ul');
            optionsList.className = 'options-list';
            
            // Check if options exist and are in the expected format
            if (Array.isArray(question.options) && question.options.length > 0) {
                question.options.forEach((option, optIndex) => {
                    const optionItem = document.createElement('li');
                    optionItem.className = 'option-item';
                    if (userAnswers[questionId] === optIndex) {
                        optionItem.classList.add('selected');
                    }
                    
                    optionItem.innerHTML = `
                        <div class="option-radio"></div>
                        <div class="option-text">${option}</div>
                    `;
                    
                    optionItem.addEventListener('click', () => {
                        selectAnswer(questionId, optIndex);
                        
                        // Update UI for selection
                        document.querySelectorAll('.option-item').forEach(item => {
                            item.classList.remove('selected');
                        });
                        optionItem.classList.add('selected');
                    });
                    
                    optionsList.appendChild(optionItem);
                });
                
                questionElement.appendChild(optionsList);
            } else {
                // Handle case where options are missing
                const errorMsg = document.createElement('div');
                errorMsg.className = 'error-message';
                errorMsg.textContent = 'Error: Options not available for this question.';
                questionElement.appendChild(errorMsg);
                console.error('Missing options for question:', question);
            }
        } else if (question.type === 'numerical') {
            const numericalInput = document.createElement('div');
            numericalInput.className = 'numerical-input';
            
            numericalInput.innerHTML = `
                <div class="input-label">Enter your answer:</div>
                <input type="number" class="numerical-value" step="0.01" value="${userAnswers[questionId] || ''}">
            `;
            
            const input = numericalInput.querySelector('input');
            input.addEventListener('input', () => {
                selectAnswer(questionId, parseFloat(input.value));
            });
            
            questionElement.appendChild(numericalInput);
        }
        
        // Add question to container
        questionContainer.appendChild(questionElement);
        
        // Update navigation buttons
        document.getElementById('prev-btn').disabled = currentQuestionIndex === 0;
        document.getElementById('save-next-btn').textContent = 
            currentQuestionIndex === questionsOrder.length - 1 ? 'Save' : 'Save & Next';
        
        // Update mark button text based on current status
        const markBtn = document.getElementById('mark-btn');
        if (questionStatus[questionId] === 'marked' || questionStatus[questionId] === 'answered-and-marked') {
            markBtn.innerHTML = '<i class="fas fa-flag"></i> Unmark';
        } else {
            markBtn.innerHTML = '<i class="fas fa-flag"></i> Mark for Review';
        }
        
        if (window.MathJax) {
            window.MathJax.typeset();
        }
    }
    
    // Select an answer for a question
    // Modify the selectAnswer function to record attempts
    function selectAnswer(questionId, answerIndex) {
        userAnswers[questionId] = answerIndex;
        
        // Record this attempt
        recordQuestionAttempt(questionId, answerIndex);
        
        // Update question status
        if (questionStatus[questionId] === 'not-answered' || questionStatus[questionId] === 'not-visited') {
            questionStatus[questionId] = 'answered';
        } else if (questionStatus[questionId] === 'marked') {
            questionStatus[questionId] = 'answered-and-marked';
        }
        
        updatePalette();
        updateProgressStats();
    }
    
    // Mark/unmark question for review
    function toggleMarkQuestion() {
        const questionId = questionsOrder[currentQuestionIndex];
        
        if (questionStatus[questionId] === 'not-answered' || questionStatus[questionId] === 'not-visited') {
            questionStatus[questionId] = 'marked';
        } else if (questionStatus[questionId] === 'answered') {
            questionStatus[questionId] = 'answered-and-marked';
        } else if (questionStatus[questionId] === 'marked') {
            questionStatus[questionId] = 'not-answered';
        } else if (questionStatus[questionId] === 'answered-and-marked') {
            questionStatus[questionId] = 'answered';
        }
        
        updateUI();
    }
    
    // Clear response for current question
    function clearResponse() {
        const questionId = questionsOrder[currentQuestionIndex];
        
        // Remove from answers
        delete userAnswers[questionId];
        
        // Update status
        if (questionStatus[questionId] === 'answered') {
            questionStatus[questionId] = 'not-answered';
        } else if (questionStatus[questionId] === 'answered-and-marked') {
            questionStatus[questionId] = 'marked';
        }
        
        // Update UI for the specific question
        loadQuestion(currentQuestionIndex);
        updatePalette();
        updateProgressStats();
    }
    
    // Update question palette
    function updatePalette() {
        const palette = document.getElementById('question-palette-body');
        palette.innerHTML = '';
        
        questionsOrder.forEach((questionId, index) => {
            const questionButton = document.createElement('div');
            questionButton.className = `question-number ${questionStatus[questionId]}`;
            questionButton.textContent = index + 1;
            
            if (index === currentQuestionIndex) {
                questionButton.classList.add('current');
            }
            
            questionButton.addEventListener('click', () => {
                loadQuestion(index);
                updatePalette();
            });
            
            palette.appendChild(questionButton);
        });
    }
    
    // Update progress statistics
    function updateProgressStats() {
        let answeredCount = 0;
        
        for (const questionId in questionStatus) {
            if (questionStatus[questionId] === 'answered' || questionStatus[questionId] === 'answered-and-marked') {
                answeredCount++;
            }
        }
        
        const totalQuestions = questionsOrder.length;
        const remainingCount = totalQuestions - answeredCount;
        const progressPercent = (answeredCount / totalQuestions) * 100;
        
        document.getElementById('answered-count').textContent = answeredCount;
        document.getElementById('remaining-count').textContent = remainingCount;
        document.getElementById('progress-fill').style.width = `${progressPercent}%`;
    }
    
    // Show the submit confirmation dialog
    function showSubmitDialog() {
        const submitModal = document.getElementById('submit-modal');
        const submitSummary = document.getElementById('submit-summary');
        
        let answeredCount = 0;
        let markedCount = 0;
        let notAnsweredCount = 0;
        let notVisitedCount = 0;
        
        for (const questionId in questionStatus) {
            const status = questionStatus[questionId];
            if (status === 'answered' || status === 'answered-and-marked') {
                answeredCount++;
            }
            if (status === 'marked' || status === 'answered-and-marked') {
                markedCount++;
            }
            if (status === 'not-answered') {
                notAnsweredCount++;
            }
            if (status === 'not-visited') {
                notVisitedCount++;
            }
        }
        
        submitSummary.innerHTML = `
            <div class="summary-stats">
                <div class="summary-item">
                    <div class="summary-label">Questions Answered</div>
                    <div class="summary-value">${answeredCount} / ${questionsOrder.length}</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">Questions Marked</div>
                    <div class="summary-value">${markedCount}</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">Not Answered</div>
                    <div class="summary-value">${notAnsweredCount}</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">Not Visited</div>
                    <div class="summary-value">${notVisitedCount}</div>
                </div>
            </div>
        `;
        
        submitModal.style.display = 'block';
    }
    
    // Submit the test
    function submitTest() {
        clearInterval(timerInterval);
        
        // Ensure we record time spent on the final question
        const now = Date.now();
        const questionId = questionsOrder[currentQuestionIndex];
        const timeOnQuestion = now - currentQuestionStartTime;
        
        if (!questionTimings[questionId]) {
            questionTimings[questionId] = 0;
        }
        questionTimings[questionId] += timeOnQuestion;
        
        // Calculate score
        let correctCount = 0;
        const totalQuestions = questionsOrder.length;
        
        for (const questionId in userAnswers) {
            const question = questionsById[questionId];
            const userAnswer = userAnswers[questionId];
            
            if (question.type === 'mcq' && question.answer === userAnswer) {
                correctCount++;
            } else if (question.type === 'numerical' && Math.abs(question.answer - userAnswer) < 0.01) {
                correctCount++;
            }
        }
        
        const scorePercent = ((correctCount / totalQuestions) * 100).toFixed(1);
        
        // Record daily task completion
        fetch('/api/daily-task/complete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                correct_count: correctCount,
                total_questions: totalQuestions,
                time_spent: timeSpent
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert('Error: ' + data.error);
                return;
            }
            
            // Update the streak display
            document.getElementById('final-streak-count').textContent = data.current_streak;
            document.getElementById('new-streak-count').textContent = data.current_streak;
            document.getElementById('final-score').textContent = scorePercent + '%';
            
            // Show success modal
            document.getElementById('submit-modal').style.display = 'none';
            document.getElementById('success-modal').style.display = 'block';
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while submitting. Please try again.');
        });
    }
    
    // Add this function after the selectAnswer function
    function recordQuestionAttempt(questionId, userAnswer) {
        // Get the current question
        const question = questionsById[questionId];
        if (!question) return;
        
        // Determine if the answer is correct
        let isCorrect = false;
        if (question.type === 'mcq') {
            isCorrect = userAnswer === question.answer;
        } else if (question.type === 'numerical') {
            // For numerical questions, allow a small margin of error
            isCorrect = Math.abs(userAnswer - question.answer) < 0.01;
        }
        
        // Send the attempt to the server to record activity
        fetch('/api/daily-task/record-attempt', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                question_id: questionId,
                user_answer: userAnswer,
                is_correct: isCorrect
            })
        })
        .then(response => response.json())
        .catch(error => {
            console.error('Error recording question attempt:', error);
        });
        
        return isCorrect;
    }
    
    // Event listeners
    document.getElementById('prev-btn').addEventListener('click', () => {
        if (currentQuestionIndex > 0) {
            loadQuestion(currentQuestionIndex - 1);
            updatePalette();
        }
    });
    
    document.getElementById('save-next-btn').addEventListener('click', () => {
        if (currentQuestionIndex < questionsOrder.length - 1) {
            loadQuestion(currentQuestionIndex + 1);
            updatePalette();
        } else {
            showSubmitDialog();
        }
    });
    
    document.getElementById('mark-btn').addEventListener('click', toggleMarkQuestion);
    document.getElementById('clear-btn').addEventListener('click', clearResponse);
    document.getElementById('submit-task-btn').addEventListener('click', showSubmitDialog);
    
    // Modal close buttons
    document.getElementById('close-submit-modal').addEventListener('click', () => {
        document.getElementById('submit-modal').style.display = 'none';
    });
    
    document.getElementById('cancel-submit').addEventListener('click', () => {
        document.getElementById('submit-modal').style.display = 'none';
    });
    
    document.getElementById('confirm-submit').addEventListener('click', submitTest);
    
    // Click outside to close modals
    window.addEventListener('click', (event) => {
        const submitModal = document.getElementById('submit-modal');
        if (event.target === submitModal) {
            submitModal.style.display = 'none';
        }
    });
    
    // Initialize the test
    initializeTest();
    initializeTimer();
});