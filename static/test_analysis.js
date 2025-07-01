document.addEventListener('DOMContentLoaded', function() {
    // Initialize the score progress circle
    updateScoreCircle();
    
    // Initialize subject analysis, topic analysis, and difficulty chart for the latest attempt
    if (attemptsData.length > 0) {
        const latestAttempt = attemptsData[attemptsData.length - 1];
        generateSubjectAnalysis(latestAttempt);
        generateTopicAnalysis(latestAttempt);
        generateDifficultyChart(latestAttempt);
    }
    
    // Add event listener to attempt selector
    const attemptSelect = document.getElementById('attempt-select');
    if (attemptSelect) {
        attemptSelect.addEventListener('change', function() {
            updateAnalysisForAttempt(this.value);
        });
    }
    updateAnalysisForAttempt(attemptSelect ? attemptSelect.value : attemptsData[0]._id);
});

function updateScoreCircle() {
    if (attemptsData.length === 0) return;
    
    const latestAttempt = attemptsData[attemptsData.length - 1];
    const scorePercentage = (latestAttempt.score / testData.max_marks) * 100;
    
    const scoreProgress = document.getElementById('score-progress');
    if (scoreProgress) {
        scoreProgress.style.setProperty('--progress', `${scorePercentage}%`);
    }
}

function updateAnalysisForAttempt(attemptId) {
    // Find the selected attempt
    const selectedAttempt = attemptsData.find(attempt => attempt._id === attemptId);
    if (!selectedAttempt) return;
    
    // Update score display
    const currentScore = document.querySelector('.current-score');
    if (currentScore) {
        currentScore.textContent = Math.round(selectedAttempt.score);
    }
    
    // Update score circle
    const scorePercentage = (selectedAttempt.score / testData.max_marks) * 100;
    const scoreProgress = document.getElementById('score-progress');
    if (scoreProgress) {
        scoreProgress.style.setProperty('--progress', `${scorePercentage}%`);
    }
    
    // Update metrics
    const metricValues = document.querySelectorAll('.metric-value');
    if (metricValues.length >= 6) {
        metricValues[0].textContent = selectedAttempt.stats.attempted;
        metricValues[1].textContent = selectedAttempt.stats.correct;
        metricValues[2].textContent = selectedAttempt.stats.incorrect;
        metricValues[3].textContent = `${Math.round(selectedAttempt.stats.accuracy * 100)}%`;
        metricValues[4].textContent = selectedAttempt.stats.unanswered;
        
        // Convert time spent from seconds to minutes
        const timeSpentMinutes = Math.round(selectedAttempt.time_spent / 1000 / 60);
        metricValues[5].textContent = `${timeSpentMinutes} min`;
    }
    
    // Update subject analysis, topic analysis, and difficulty chart
    generateSubjectAnalysis(selectedAttempt);
    generateTopicAnalysis(selectedAttempt);
    generateDifficultyChart(selectedAttempt);
}

// Function to generate subject-wise analysis
function generateSubjectAnalysis(attempt) {
    const subjectAnalysisBody = document.getElementById('subject-analysis-body');
    if (!subjectAnalysisBody) return;
    
    subjectAnalysisBody.innerHTML = '';
    
    for (const [key, value] of Object.entries(testData.subjects || {})) {
        const subject = value;
        if (!subject) continue;
        
        const subjectQuestions = [];

        for (const [key, question] of Object.entries(questionsData)) {
            if (question.subject === subject._id) {
                subjectQuestions.push(question._id);
            }
        }
        
        // Count feedback items for this subject
        const subjectFeedback = attempt.feedback.filter(item => 
            subjectQuestions.includes(item.question_id)
        );
        
        const totalQuestions = subjectQuestions.length;
        const attempted = subjectFeedback.length;
        const correct = subjectFeedback.filter(item => item.correct).length;
        const incorrect = attempted - correct;
        const accuracy = attempted > 0 ? (correct / attempted) * 100 : 0;
        
        // Create table row
        const tr = document.createElement('tr');
        
        tr.innerHTML = `
            <td><span class="subject-name">${subject.name}</span></td>
            <td>${totalQuestions}</td>
            <td>${attempted}</td>
            <td class="text-success">${correct}</td>
            <td class="text-danger">${incorrect}</td>
            <td>
                <div class="accuracy-cell">
                    <span>${Math.round(accuracy)}%</span>
                    <div class="accuracy-bar">
                        <div class="accuracy-progress" style="width: ${accuracy}%"></div>
                    </div>
                </div>
            </td>
        `;
        
        subjectAnalysisBody.appendChild(tr);
    }
}

// Function to generate topic/chapter-wise analysis
function generateTopicAnalysis(attempt) {
    const topicAnalysisBody = document.getElementById('topic-analysis-body');
    if (!topicAnalysisBody) return;
    
    // Clear previous data
    topicAnalysisBody.innerHTML = '';
    
    // Create a mapping of topics by combining question data
    const topicData = {};
    
    // Process all questions to organize by topic/chapter
    for (const [questionId, question] of Object.entries(questionsData)) {
        if (!question.chapter) continue;

        // console.log(testData.subjects)
        
        const topicKey = question.chapter;
        const subjectId = question.subject;
        const subjectName = testData.subjects[subjectId] ? testData.subjects[subjectId].name : 'Unknown';
        
        // loop throuh the subject of test, it contains a chapter key which has list of all [chapID, chap name], get the topic name from there
        let topicName = '';
        for (let [subID, chaps] of Object.entries(testData.subjects)) {
            if (subID === subjectId) {
                chaps = chaps.chapters || [];
                for (const chap of chaps) {
                    if (chap[0] === question.chapter) {
                        topicName = chap[1];
                        break;
                    }
                }
            }
        }

        // Initialize topic data if it doesn't exist
        if (!topicData[topicKey]) {
            topicData[topicKey] = {
                name: topicName || 'Unknown',
                subject: subjectName,
                subjectId: subjectId,
                questions: [],
                attempted: 0,
                correct: 0
            };
        }
        
        topicData[topicKey].questions.push(questionId);
        
        // Check if this question was attempted
        const feedback = attempt.feedback.find(f => f.question_id === questionId);
        if (feedback) {
            topicData[topicKey].attempted++;
            if (feedback.correct) {
                topicData[topicKey].correct++;
            }
        }
    }
    
    // Convert to array and sort by subject and then topic name
    const sortedTopics = Object.values(topicData).sort((a, b) => {
        if (a.subject !== b.subject) {
            return a.subject.localeCompare(b.subject);
        }
        return a.name.localeCompare(b.name);
    });
    
    // Create table rows for each topic
    sortedTopics.forEach(topic => {
        // Calculate accuracy
        let accuracy = topic.attempted > 0 ? (topic.correct / topic.attempted) * 100 : 0;

        if (topic.attempted == 0) {
            accuracy = 'N/A'
        } else {
            // Ensure accuracy is a number
            accuracy = `${Math.round(accuracy)}%`;
        }
        
        // Create table row
        const tr = document.createElement('tr');
        
        tr.innerHTML = `
            <td><span class="topic-name">${topic.name}</span></td>
            <td><span class="topic-subject">${topic.subject}</span></td>
            <td>${topic.attempted}</td>
            <td class="text-success">${topic.correct}</td>
            <td>
                <div class="accuracy-cell">
                    <span>${accuracy}</span>
                    <div class="accuracy-bar" data-accuracy="${accuracy}">
                        <div class="accuracy-progress" style="width: ${accuracy}"></div>
                    </div>
                </div>
            </td>
        `;
        
        topicAnalysisBody.appendChild(tr);
    });
}

// Function to generate difficulty analysis chart
function generateDifficultyChart(attempt) {
    const canvas = document.getElementById('difficultyChart');
    if (!canvas) return;
    
    // Categorize questions by difficulty level
    const difficultyData = {
        easy: { attempted: 0, correct: 0 },
        medium: { attempted: 0, correct: 0 },
        hard: { attempted: 0, correct: 0 }
    };
    
    // Process all questions in the attempt feedback
    attempt.feedback.forEach(feedbackItem => {
        const question = questionsData[feedbackItem.question_id];
        if (!question) return;
        // Determine question difficulty (use difficulty field if available, or fallback to estimating from marking_scheme)
        let difficulty = '';
        if (question.level == 1) {
            difficulty = 'easy';
        } else if (question.level == 2) {
            difficulty = 'medium';
        } else if (question.level == 3) {
            difficulty = 'hard';
        }

        // Increment attempted count
        if (difficultyData[difficulty]) {
            difficultyData[difficulty].attempted++;
            
            // If the answer was correct, increment correct count
            if (feedbackItem.correct) {
                difficultyData[difficulty].correct++;
            }
        }
    });
    
    // If we don't have actual difficulty data, use dummy data for demonstration
    // if (difficultyData.easy.attempted === 0 && 
    //     difficultyData.medium.attempted === 0 && 
    //     difficultyData.hard.attempted === 0) {
        
    //     // Sample data based on the image
    //     difficultyData.easy = { attempted: 6, correct: 4 };
    //     difficultyData.medium = { attempted: 6, correct: 3 };
    //     difficultyData.hard = { attempted: 3, correct: 3 };
    // }
    
    // Destroy previous chart if it exists
    if (window.difficultyChart) {
        try {
            window.difficultyChart.destroy();
        } catch (error) {
            console.error('Error destroying previous chart:', error);
        }
    }
    
    // Create chart
    window.difficultyChart = new Chart(canvas, {
        type: 'bar',
        data: {
            labels: ['Easy', 'Medium', 'Hard'],
            datasets: [
                {
                    label: 'Attempted',
                    data: [
                        difficultyData.easy.attempted,
                        difficultyData.medium.attempted,
                        difficultyData.hard.attempted
                    ],
                    backgroundColor: 'rgba(99, 132, 255, 0.6)',
                    borderColor: 'rgba(99, 132, 255, 1)',
                    borderWidth: 1
                },
                {
                    label: 'Correct',
                    data: [
                        difficultyData.easy.correct,
                        difficultyData.medium.correct,
                        difficultyData.hard.correct
                    ],
                    backgroundColor: 'rgba(75, 192, 128, 0.6)',
                    borderColor: 'rgba(75, 192, 128, 1)',
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: 'rgba(255, 255, 255, 0.7)'
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: 'rgba(255, 255, 255, 0.7)'
                    }
                }
            },
            plugins: {
                legend: {
                    labels: {
                        color: 'rgba(255, 255, 255, 0.7)'
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.7)',
                    titleColor: 'rgba(255, 255, 255, 0.9)',
                    bodyColor: 'rgba(255, 255, 255, 0.9)',
                    displayColors: true,
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            label += context.parsed.y;
                            return label;
                        }
                    }
                }
            }
        }
    });
}

// Function to generate question-wise analysis
function generateQuestionAnalysis(attempt) {
    // Implementation for question analysis if needed
}
