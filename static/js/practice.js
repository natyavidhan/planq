document.addEventListener('DOMContentLoaded', function() {
    // Initialize variables
    let currentQuestionIndex = 0;
    let currentSubjectId = null;
    let questionStatus = {};
    let userAnswers = {};
    let questionAttempts = {}; // Track number of attempts per question
    let timeSpent = 0;
    let timerInterval;
    let health = 100;
    let questionsById = {};
    let questionsOrder = [];
    let isRetryMode = false;
    let incorrectQuestions = [];
    
    // New variables for question timing
    let questionStartTime = Date.now();
    let questionTimings = {};
    let currentQuestionId = null;
    let questionTimerInterval = null;
    
    // Process test data
    function initializeTest() {
        let questionNumber = 1;

        console.log("Initializing test with data:", testData);
        
        for (const subject in testData.questions) {
            currentSubjectId = subject;

            console.log(`Processing subject: ${subject}`);
            
            for (const questionId of testData.questions[subject]) {
                // Get question data from the test data
                const questionData = testData.question_data[questionId];
                const question = questionData;

                console.log(`Processing question ID: ${question}`);
                
                if (question) {
                    // Process question data
                    const processedQuestion = {
                        _id: question._id,
                        text: question.question,
                        type: question.type === 'singleCorrect' ? 'mcq' : (question.type || 'mcq'),
                        options: question.options || [],
                        answer: question.correct_option ? question.correct_option[0] : null,
                        subject: subject,
                        questionNumber: questionNumber++,
                        difficulty: question.level || 2, // Default to medium difficulty
                        attempted: false,
                        correct: false
                    };
                    
                    if (question.type === 'numerical') {
                        processedQuestion.answer = question.correct_value;
                    }
                    
                    questionsById[questionId] = processedQuestion;
                    questionsOrder.push(questionId);
                    
                    // Initialize question status
                    questionStatus[questionId] = 'unattempted';
                    questionAttempts[questionId] = 0;
                }
            }
        }
        
        console.log("Processed questions:", questionsById);
        
        // Setup start screen
        setupStartScreen();
    }
    
    // Set up the start screen
    function setupStartScreen() {
        const startBtn = document.getElementById('start-task-btn');
        startBtn.addEventListener('click', startTask);
    }
    
    // Start the task
    function startTask() {
        // Hide start screen
        document.getElementById('start-screen').style.display = 'none';
        
        // Show task content
        document.getElementById('task-content').style.display = 'flex';
        
        // Initialize UI
        updateUI();
        
        // Start timer
        initializeTimer();
    }
    
    // Initialize the main task timer
    function initializeTimer() {
        const duration = testData.duration * 60; // Convert to seconds
        let timer = duration;
        
        timerInterval = setInterval(() => {
            timeSpent++;
            timer--;
            
            if (timer < 0) {
                // Time's up - auto-submit
                clearInterval(timerInterval);
                checkCompletion();
                return;
            }
            
            updateMainTimerDisplay(timer);
        }, 1000);
    }
    
    // Update the main timer display in the header
    function updateMainTimerDisplay(seconds) {
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
        
        // Update health display
        document.getElementById('health-fill').style.width = `${health}%`;
        document.getElementById('health-percent').textContent = `${Math.round(health)}%`;
        
        // Typeset MathJax if available
        if (window.MathJax) {
            window.MathJax.typeset();
        }
    }
    
    // Update loadQuestion to not use correct answers for UI updates
    function loadQuestion(index) {
        if (index < 0 || index >= questionsOrder.length) {
            return;
        }
        
        // Record time spent on previous question when switching
        if (currentQuestionId) {
            const timeSpent = Date.now() - questionStartTime;
            questionTimings[currentQuestionId] = (questionTimings[currentQuestionId] || 0) + timeSpent;
        }
        
        // Reset timer for the new question
        currentQuestionIndex = index;
        const questionId = questionsOrder[index];
        currentQuestionId = questionId;
        questionStartTime = Date.now();
        const question = questionsById[questionId];
        
        // Start timer for this question
        startQuestionTimer();
        
        const questionContainer = document.getElementById('question-container');
        
        // Clear previous content
        questionContainer.innerHTML = '';
        
        // Create question element
        const questionElement = document.createElement('div');
        questionElement.className = 'question';
        
        // Question number and text with timer badge
        const questionText = document.createElement('div');
        questionText.className = 'question-text';
        questionText.innerHTML = `
            <div class="question-header">
                <div class="question-number-display">Question ${question.questionNumber} of ${questionsOrder.length}</div>
                <div class="question-badges">
                    <span class="question-type-badge">${question.type === 'mcq' ? 'MCQ' : 'Numerical'}</span>
                    <span class="timer-badge" id="timer-badge">00:00</span>
                </div>
            </div>
            <div class="question-content">
                <strong>Q${question.questionNumber}.</strong> ${question.text}
            </div>
        `;
        questionElement.appendChild(questionText);
        
        // Options
        if (question.type === 'mcq' || question.type === 'singleCorrect') {
            const optionsList = document.createElement('ul');
            optionsList.className = 'options-list';
            
            if (Array.isArray(question.options) && question.options.length > 0) {
                question.options.forEach((option, optIndex) => {
                    const optionItem = document.createElement('li');
                    optionItem.className = 'option-item';
                    
                    // If question was already attempted, show user's answer
                    if (question.attempted) {
                        if (userAnswers[questionId] === optIndex) {
                            optionItem.classList.add(question.correct ? 'selected-correct' : 'selected-incorrect');
                        }
                    }
                    
                    optionItem.innerHTML = `
                        <div class="option-radio"></div>
                        <div class="option-text">${option}</div>
                    `;
                    
                    // Only allow selection if question hasn't been attempted or we're in retry mode
                    if (!question.attempted || (isRetryMode && incorrectQuestions.includes(questionId))) {
                        optionItem.addEventListener('click', () => {
                            selectAnswer(questionId, optIndex);
                        });
                    } else {
                        optionItem.classList.add('disabled');
                    }
                    
                    optionsList.appendChild(optionItem);
                });
                
                questionElement.appendChild(optionsList);
            } else {
                const errorMsg = document.createElement('div');
                errorMsg.className = 'error-message';
                errorMsg.textContent = 'Error: Options not available for this question.';
                questionElement.appendChild(errorMsg);
            }
        } else if (question.type === 'numerical') {
            const numericalInput = document.createElement('div');
            numericalInput.className = 'numerical-input';
            
            numericalInput.innerHTML = `
                <div class="input-label">Enter your answer:</div>
                <input type="number" class="numerical-value" step="0.01" value="${userAnswers[questionId] || ''}">
                <button class="submit-numerical">Submit Answer</button>
            `;
            
            const input = numericalInput.querySelector('input');
            const submitBtn = numericalInput.querySelector('button');
            
            // If question was already attempted and not in retry mode, disable the input
            if (question.attempted && !(isRetryMode && incorrectQuestions.includes(questionId))) {
                input.disabled = true;
                submitBtn.disabled = true;
                submitBtn.classList.add('disabled');
            } else {
                submitBtn.addEventListener('click', () => {
                    const value = parseFloat(input.value);
                    if (!isNaN(value)) {
                        selectAnswer(questionId, value);
                    } else {
                        alert('Please enter a valid number');
                    }
                });
            }
            
            questionElement.appendChild(numericalInput);
        }
        
        // Add question to container
        questionContainer.appendChild(questionElement);
        
        // Update the feedback area if the question has been attempted
        updateFeedbackArea(questionId);
        
        // Update navigation buttons
        document.getElementById('prev-btn').disabled = currentQuestionIndex === 0;
        document.getElementById('next-btn').textContent = 
            currentQuestionIndex === questionsOrder.length - 1 ? 'Finish' : 'Next';
        
        // Update the timer display immediately
        const prevTime = questionTimings[currentQuestionId] || 0;
        updateQuestionTimerDisplay(prevTime);
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
            updateQuestionTimerDisplay(totalTime);
        }, 100); // Update more frequently for better responsiveness
    }
    
    // Update question timer display
    function updateQuestionTimerDisplay(timeInMs) {
        // Convert to seconds and format
        const totalSeconds = Math.floor(timeInMs / 1000);
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = totalSeconds % 60;
        const formattedTime = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        
        // Update timer in the question header
        const timerBadge = document.getElementById('timer-badge');
        if (timerBadge) {
            timerBadge.textContent = formattedTime;
        }
    }
    
    // Update feedback area for a question
    function updateFeedbackArea(questionId, damageDone = 0) {
        const question = questionsById[questionId];
        const feedbackArea = document.getElementById('answer-feedback');
        
        if (question.attempted) {
            feedbackArea.style.display = 'flex';
            
            if (question.correct) {
                feedbackArea.className = 'answer-feedback correct';
                feedbackArea.innerHTML = `<i class="fas fa-check-circle"></i> <span>Correct answer!</span>`;
            } else {
                feedbackArea.className = 'answer-feedback incorrect';
                feedbackArea.innerHTML = `<i class="fas fa-times-circle"></i> <span>Incorrect. Health -${damageDone}%</span>`;
            }
        } else {
            feedbackArea.style.display = 'none';
        }
    }
    
    // Select an answer for a question
    function selectAnswer(questionId, answer) {
        const question = questionsById[questionId];
        
        // Store the user's answer
        userAnswers[questionId] = answer;
        
        // Get the time spent on this question so far
        const currentTime = Date.now();
        const timeSpent = currentTime - questionStartTime;
        const totalTimeSpent = (questionTimings[questionId] || 0) + timeSpent;
        questionTimings[questionId] = totalTimeSpent;
        
        // Reset question start time to now, so timing continues correctly
        questionStartTime = currentTime;
        
        // Increment attempt count
        questionAttempts[questionId]++;
        
        // Mark as attempted for UI purposes, but don't determine if correct yet
        question.attempted = true;
        
        // Send answer to backend for validation and get result
        submitAnswer(questionId, answer, totalTimeSpent);
    }
    
    // Update the submitAnswer function to use server-provided health and damage values
    function submitAnswer(questionId, answer, timeTaken) {
        // AJAX request to submit the answer and get validation
        fetch('/practice', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                question_id: questionId,
                user_answer: answer,
                time_taken: timeTaken
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error('Error:', data.error);
                return;
            }
            
            // Now update the UI based on server's validation
            const question = questionsById[questionId];
            const isCorrect = data.is_correct;
            
            // Update question status
            question.correct = isCorrect;
            questionStatus[questionId] = isCorrect ? 'correct' : 'incorrect';
            
            // Use health value from server instead of calculating locally
            health = data.health_remaining;
            
            // Update the UI to show the result with server-provided values
            updateUI();
            updateFeedbackArea(questionId, data.damage_done || 0);
            
            // Only auto advance if this is the last attempt and answer is INCORRECT
            // Remove auto-advancing on correct answers
            if (!isCorrect && questionAttempts[questionId] >= 2) {
                setTimeout(() => {
                    if (currentQuestionIndex < questionsOrder.length - 1) {
                        currentQuestionIndex++;
                        updateUI();
                    }
                }, 1500);
            }
        })
        .catch(error => {
            console.error('Error submitting answer:', error);
        });
    }
    
    // Calculate health damage based on difficulty
    function calculateHealthDamage(difficulty) {
        const totalQuestions = questionsOrder.length;
        const difficultyMultiplier = difficulty === 1 ? 1.2 : (difficulty === 2 ? 1 : 0.8);
        
        // damage = 100 / sqrt(n) * difficulty_multiplier
        return (100 / Math.sqrt(totalQuestions)) * difficultyMultiplier;
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
                updateUI();
            });
            
            palette.appendChild(questionButton);
        });
    }
    
    // Update progress statistics
    function updateProgressStats() {
        let answeredCount = 0;
        let correctCount = 0;
        
        for (const questionId in questionStatus) {
            const status = questionStatus[questionId];
            if (status === 'correct' || status === 'incorrect') {
                answeredCount++;
            }
            if (status === 'correct') {
                correctCount++;
            }
        }
        
        const totalQuestions = questionsOrder.length;
        const remainingCount = totalQuestions - answeredCount;
        const progressPercent = (answeredCount / totalQuestions) * 100;
        
        document.getElementById('answered-count').textContent = answeredCount;
        document.getElementById('remaining-count').textContent = remainingCount;
        document.getElementById('progress-fill').style.width = `${progressPercent}%`;
    }
    
    // Check if all questions have been attempted and show appropriate screen
    function checkCompletion() {
        // Record time for the current question
        if (currentQuestionId) {
            const timeSpent = Date.now() - questionStartTime;
            questionTimings[currentQuestionId] = (questionTimings[currentQuestionId] || 0) + timeSpent;
        }
        
        // Stop question timer
        if (questionTimerInterval) {
            clearInterval(questionTimerInterval);
            questionTimerInterval = null;
        }
        
        // Count correct and incorrect questions
        const correctQuestions = [];
        incorrectQuestions = []; // Reset the global incorrectQuestions array
        
        for (const questionId in questionsById) {
            const question = questionsById[questionId];
            if (question.attempted && question.correct) {
                correctQuestions.push(questionId);
            } else if (question.attempted && !question.correct) {
                incorrectQuestions.push(questionId);
            }
        }
        
        // If not all questions attempted, prompt user
        const unattemptedCount = questionsOrder.length - (correctQuestions.length + incorrectQuestions.length);
        
        if (unattemptedCount > 0 && health > 0) {
            const confirmContinue = confirm(`You have ${unattemptedCount} unattempted questions. Do you want to continue anyway?`);
            if (!confirmContinue) {
                // Find first unattempted question
                const unattemptedIndex = questionsOrder.findIndex(qId => !questionsById[qId].attempted);
                if (unattemptedIndex >= 0) {
                    currentQuestionIndex = unattemptedIndex;
                    updateUI();
                    return;
                }
            }
        }
        
        // If health is 0, show fail screen
        if (health <= 0) {
            showFailScreen();
            return;
        }
        
        // If there are incorrect questions and health > 0, show retry screen
        if (incorrectQuestions.length > 0) {
            showRetryScreen(correctQuestions.length, incorrectQuestions.length);
        } else {
            // All correct, show success screen
            showSuccessScreen();
        }
    }
    
    // Show retry screen
    function showRetryScreen(correctCount, incorrectCount) {
        // Stop question timer
        if (questionTimerInterval) {
            clearInterval(questionTimerInterval);
            questionTimerInterval = null;
        }
        
        // Hide task content
        document.getElementById('task-content').style.display = 'none';
        
        // Show retry screen
        const retryScreen = document.getElementById('retry-screen');
        retryScreen.style.display = 'block';
        
        // Update retry screen content
        document.getElementById('retry-health').textContent = `${Math.round(health)}%`;
        document.getElementById('correct-count').textContent = correctCount;
        document.getElementById('incorrect-count').textContent = incorrectCount;
        
        // Add event listener to retry button
        document.getElementById('retry-btn').addEventListener('click', startRetry);
    }
    
    // Start retry mode
    function startRetry() {
        isRetryMode = true;
        
        // Hide retry screen
        document.getElementById('retry-screen').style.display = 'none';
        
        // Show task content
        document.getElementById('task-content').style.display = 'flex';
        
        // Set current question to first incorrect question
        const firstIncorrectIndex = questionsOrder.findIndex(qId => incorrectQuestions.includes(qId));
        if (firstIncorrectIndex >= 0) {
            currentQuestionIndex = firstIncorrectIndex;
        }
        
        // Update question status for retry
        for (const questionId of incorrectQuestions) {
            questionStatus[questionId] = 'retry';
            questionsById[questionId].attempted = false; // Allow another attempt
        }
        
        // Update UI
        updateUI();
    }
    
    // Show fail screen
    function showFailScreen() {
        // Clear timer intervals
        if (timerInterval) {
            clearInterval(timerInterval);
            timerInterval = null;
        }
        
        if (questionTimerInterval) {
            clearInterval(questionTimerInterval);
            questionTimerInterval = null;
        }
        
        // Hide task content
        document.getElementById('task-content').style.display = 'none';
        
        // Show fail screen
        document.getElementById('fail-screen').style.display = 'block';
        
        // Add event listener to restart button
        document.getElementById('restart-btn').addEventListener('click', () => {
            window.location.href = '/practice/generate?exam=' + testData.exam + '&subject=' + testData.subject + '&chapter=' + testData.chapter + '&count=' + questionsOrder.length + '&time=' + testData.duration;
        });
    }
    
    // Show success screen with confetti animation
    function showSuccessScreen() {
        // Clear timer intervals
        if (timerInterval) {
            clearInterval(timerInterval);
            timerInterval = null;
        }
        
        if (questionTimerInterval) {
            clearInterval(questionTimerInterval);
            questionTimerInterval = null;
        }
        
        // Hide task content
        document.getElementById('task-content').style.display = 'none';
        
        // Show success screen
        document.getElementById('success-screen').style.display = 'block';
        
        // Update final health
        document.getElementById('final-health').textContent = `${Math.round(health)}%`;
        
        // Create confetti
        createConfetti();
        
        // Submit final results
        submitCompletion();
    }
    
    // Create confetti animation
    function createConfetti() {
        const container = document.getElementById('confetti-container');
        const colors = ['#f43f5e', '#3b82f6', '#22c55e', '#eab308', '#8b5cf6'];
        
        for (let i = 0; i < 100; i++) {
            const confetti = document.createElement('div');
            confetti.className = 'confetti';
            confetti.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
            confetti.style.left = Math.random() * 100 + '%';
            confetti.style.top = -10 + 'px';
            confetti.style.width = Math.random() * 10 + 5 + 'px';
            confetti.style.height = Math.random() * 10 + 5 + 'px';
            confetti.style.opacity = Math.random();
            confetti.style.transform = `rotate(${Math.random() * 360}deg)`;
            
            // Random shapes
            const shapes = ['circle', 'square', 'triangle'];
            const shape = shapes[Math.floor(Math.random() * shapes.length)];
            if (shape === 'circle') {
                confetti.style.borderRadius = '50%';
            } else if (shape === 'triangle') {
                confetti.style.width = 0;
                confetti.style.height = 0;
                confetti.style.backgroundColor = 'transparent';
                confetti.style.borderLeft = '5px solid transparent';
                confetti.style.borderRight = '5px solid transparent';
                confetti.style.borderBottom = '10px solid ' + colors[Math.floor(Math.random() * colors.length)];
            }
            
            // Animation
            const duration = Math.random() * 3 + 2;
            const delay = Math.random() * 2;
            
            confetti.style.animation = `confettiFall ${duration}s ease ${delay}s forwards`;
            
            // Add the confetti to the container
            container.appendChild(confetti);
            
            // Add CSS animation
            const style = document.createElement('style');
            style.innerHTML = `
                @keyframes confettiFall {
                    0% {
                        transform: translateY(0) rotate(${Math.random() * 360}deg);
                    }
                    100% {
                        transform: translateY(${container.offsetHeight}px) rotate(${Math.random() * 360}deg);
                    }
                }
            `;
            document.head.appendChild(style);
        }
    }
    
    // Submit completion to server
    function submitCompletion() {
        // Calculate correct and incorrect counts
        let correctCount = 0;
        let incorrectCount = 0;
        
        for (const questionId in questionsById) {
            const question = questionsById[questionId];
            if (question.attempted && question.correct) {
                correctCount++;
            } else if (question.attempted && !question.correct) {
                incorrectCount++;
            }
        }
        
        // AJAX request to submit completion with timing data
        fetch('/practice', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                correct_count: correctCount,
                incorrect_count: incorrectCount,
                time_spent: timeSpent,
                question_timings: questionTimings,
                health_remaining: health,
                is_success: true
            })
        })
        .then(response => response.json())
        .then(data => {
            console.log("Practice completion response:", data); // Debug logging
            
            // Update success screen based on streak extension
            if (data.streak_extended) {
                console.log("Streak extended! Updating UI...");
                document.getElementById('success-title').textContent = 'Streak Extended!';
                
                // Make sure the streak animation element is visible
                const streakAnimation = document.getElementById('streak-animation');
                if (streakAnimation) {
                    streakAnimation.style.display = 'block';
                    
                    // Update the streak count if the element exists
                    const finalStreakCount = document.getElementById('final-streak-count');
                    if (finalStreakCount) {
                        finalStreakCount.textContent = data.current_streak;
                    } else {
                        console.error("Element 'final-streak-count' not found");
                    }
                    
                    // Create extra confetti for celebration
                    createConfetti();
                } else {
                    console.error("Element 'streak-animation' not found");
                }
            } else {
                console.log("Streak not extended. Regular completion.");
                document.getElementById('success-title').textContent = 'Practice Complete!';
                
                const streakAnimation = document.getElementById('streak-animation');
                if (streakAnimation) {
                    streakAnimation.style.display = 'none';
                }
            }
        })
        .catch(error => {
            console.error('Error submitting completion:', error);
        });
    }
    
    // Event listeners for navigation buttons
    document.getElementById('prev-btn').addEventListener('click', () => {
        if (currentQuestionIndex > 0) {
            currentQuestionIndex--;
            updateUI();
        }
    });
    
    document.getElementById('next-btn').addEventListener('click', () => {
        if (currentQuestionIndex < questionsOrder.length - 1) {
            currentQuestionIndex++;
            updateUI();
        } else {
            // Last question, check completion
            checkCompletion();
        }
    });
    
    // Initialize the test
    initializeTest();
});