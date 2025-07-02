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
    
    // Initialize overall analytics if there are attempts
    if (attemptsData.length > 0) {
        generateOverallAnalytics();
        generateSubjectPerformance();
        generateAttemptsHistory();
        generateProgressChart();
    }
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
    
    // Update subject analysis, topic analysis, difficulty chart, and question analysis
    generateSubjectAnalysis(selectedAttempt);
    generateTopicAnalysis(selectedAttempt);
    generateDifficultyChart(selectedAttempt);
    generateQuestionAnalysis(selectedAttempt);
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
    const tableBody = document.getElementById('question-analysis-body');
    if (!tableBody) return;
    
    // Clear existing content
    tableBody.innerHTML = '';
    
    // Sort feedback by question index if available, or just use as is
    const feedbackItems = [...attempt.feedback];
    
    let finalData = [];

    // Process each question
    feedbackItems.forEach((feedback, index) => {
        const question = questionsData[feedback.question_id];
        if (!question) return;
        
        // Get subject name
        const subjectId = question.subject;
        const subject = testData.subjects[subjectId] ? testData.subjects[subjectId].name : 'Unknown';
        
        // Get topic/chapter name
        let topicName = 'Unknown';
        if (question.chapter) {
            for (let [subId, subjectData] of Object.entries(testData.subjects)) {
                if (subId === subjectId && subjectData.chapters) {
                    for (const chapter of subjectData.chapters) {
                        if (chapter[0] === question.chapter) {
                            topicName = chapter[1];
                            break;
                        }
                    }
                }
            }
        }
        
        // Determine difficulty level
        let difficultyClass = 'difficulty-medium';
        let difficultyText = 'MED';
        if (question.level === 1) {
            difficultyClass = 'difficulty-easy';
            difficultyText = 'EASY';
        } else if (question.level === 3) {
            difficultyClass = 'difficulty-hard';
            difficultyText = 'HARD';
        }
        
        // Format your answer and correct answer
        const userAnswer = feedback.user_answer;
        const correctAnswer = feedback.correct_answer;
        
        // Format marks (positive or negative)
        const marks = feedback.marks;
        const marksClass = marks >= 0 ? 'positive-marks' : 'negative-marks';
        
        // Format result (correct or incorrect)
        const resultIcon = feedback.correct ? '✓' : '✗';
        const resultClass = feedback.correct ? 'correct-result' : 'incorrect-result';

        finalData.push({
            questionNumber: question.question_number,
            subject: subject,
            topicName: topicName,
            difficultyClass: difficultyClass,
            difficultyText: difficultyText,
            userAnswer: userAnswer,
            correctAnswer: correctAnswer,
            marks: marks,
            resultIcon: resultIcon,
            resultClass: resultClass,
            time: question.time || '-'
        });

    });

    // Sort finalData by question number
    finalData.sort((a, b) => a.questionNumber - b.questionNumber);

    for (const q of finalData) {
        console.log(q);
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>Q${q.questionNumber}</td>
            <td>${q.subject}</td>
            <td>${q.topicName}</td>
            <td><span class="${q.difficultyClass}">${q.difficultyText}</span></td>
            <td>${q.userAnswer}</td>
            <td>${q.correctAnswer}</td>
            <td class="${q.marksClass}">${q.marks >= 0 ? '+' + q.marks : q.marks}</td>
            <td>${q.time}</td>
            <td class="${q.resultClass}">${q.resultIcon}</td>
        `;
        tableBody.appendChild(tr);
    }
}

// Function to generate overall analytics
function generateOverallAnalytics() {
    // Calculate analytics
    const totalAttempts = attemptsData.length;
    
    // Calculate average score
    const totalScore = attemptsData.reduce((sum, attempt) => sum + attempt.score, 0);
    const avgScore = totalScore / totalAttempts;
    
    // Find best and worst scores
    const scores = attemptsData.map(attempt => attempt.score);
    const bestScore = Math.max(...scores);
    const worstScore = Math.min(...scores);
    
    // Calculate average time spent (in minutes)
    const totalTimeSpent = attemptsData.reduce((sum, attempt) => sum + attempt.time_spent, 0);
    const avgTimeSpent = totalTimeSpent / totalAttempts;
    const avgMinutes = Math.floor(avgTimeSpent / 1000 / 60);
    const avgSeconds = Math.floor(avgTimeSpent / 1000 % 60);

    // Calculate improvement (difference between first and last attempt)
    let improvement = 0;
    if (totalAttempts >= 2) {
        improvement = attemptsData[attemptsData.length - 1].score - attemptsData[0].score;
    }
    
    // Update the DOM
    document.getElementById('total-attempts').textContent = totalAttempts;
    document.getElementById('avg-score').textContent = avgScore.toFixed(1);
    document.getElementById('best-score').textContent = bestScore;
    document.getElementById('worst-score').textContent = worstScore;
    document.getElementById('avg-time').textContent = `${avgMinutes}:${avgSeconds.toString().padStart(2, '0')}`;
    document.getElementById('improvement').textContent = improvement > 0 ? `+${improvement}` : improvement;
    
    // Set color for improvement
    const improvementElement = document.getElementById('improvement');
    if (improvement > 0) {
        improvementElement.style.color = 'var(--success)';
    } else if (improvement < 0) {
        improvementElement.style.color = 'var(--danger)';
    } else {
        improvementElement.style.color = 'var(--text-secondary)';
    }
}

// Function to generate subject performance data
function generateSubjectPerformance() {
    const subjectAnalysisBody = document.getElementById('overall-subject-body');
    if (!subjectAnalysisBody) return;
    
    subjectAnalysisBody.innerHTML = '';
    
    // Get all subjects from test data
    const subjectData = {};
    
    // Initialize subject data
    for (const [subjectId, subject] of Object.entries(testData.subjects)) {
        // Create a CSS-safe class name from the subject name
        const cssClass = subject.name ? subject.name.toLowerCase().replace(/[^a-z0-9]/g, '-') : '';
        
        subjectData[subjectId] = {
            name: subject.name,
            totalAttempted: 0,
            totalCorrect: 0,
            accuracy: 0,
            cssClass: cssClass
        };
    }
    
    // Process all attempts to gather subject performance data
    attemptsData.forEach(attempt => {
        attempt.feedback.forEach(item => {
            const question = questionsData[item.question_id];
            if (!question) return;
            
            const subjectId = question.subject;
            if (!subjectData[subjectId]) return;
            
            subjectData[subjectId].totalAttempted++;
            if (item.correct) {
                subjectData[subjectId].totalCorrect++;
            }
        });
    });
    
    // Calculate accuracy for each subject
    for (const subject of Object.values(subjectData)) {
        if (subject.totalAttempted > 0) {
            subject.accuracy = (subject.totalCorrect / subject.totalAttempted) * 100;
        }
    }
    
    // Create table rows for each subject
    for (const subject of Object.values(subjectData)) {
        const tr = document.createElement('tr');
        
        tr.innerHTML = `
            <td><span class="subject-name">${subject.name}</span></td>
            <td>${subject.totalAttempted}</td>
            <td>${subject.totalCorrect}</td>
            <td>
                <div class="accuracy-progress-container">
                    <div class="accuracy-bar-large">
                        <div class="accuracy-fill" style="width: ${subject.accuracy}%;"></div>
                    </div>
                    <span class="accuracy-value">${subject.accuracy.toFixed(1)}%</span>
                </div>
            </td>
        `;
        
        subjectAnalysisBody.appendChild(tr);
    }
}

// Function to generate attempts history table
function generateAttemptsHistory() {
    const attemptsHistoryBody = document.getElementById('attempts-history-body');
    if (!attemptsHistoryBody) return;
    
    attemptsHistoryBody.innerHTML = '';
    
    // Process each attempt and create table rows
    attemptsData.forEach((attempt, index) => {
        const attemptNumber = index + 1;
        const date = new Date(attempt.submitted_at);
        const formattedDate = `${date.getDate()}/${date.getMonth() + 1}/${date.getFullYear()}, ${date.getHours()}:${date.getMinutes().toString().padStart(2, '0')} ${date.getHours() >= 12 ? 'pm' : 'am'}`;
        const accuracy = attempt.stats.accuracy * 100;
        const timeSpent = attempt.time_spent;
        const minutes = Math.floor(timeSpent / 1000 / 60);
        const seconds = Math.floor(timeSpent / 1000 % 60);
        const formattedTime = `${minutes}:${seconds.toString().padStart(2, '0')}`;
        
        const tr = document.createElement('tr');
        
        tr.innerHTML = `
            <td>${attemptNumber}</td>
            <td>${formattedDate}</td>
            <td>${attempt.score}</td>
            <td>${accuracy.toFixed(1)}%</td>
            <td>${formattedTime}</td>
            <td>${attempt.stats.attempted}</td>
        `;
        
        attemptsHistoryBody.appendChild(tr);
    });
}

// Function to generate progress chart
function generateProgressChart() {
    const canvas = document.getElementById('progressChart');
    if (!canvas) return;
    
    // Prepare data for chart
    const labels = attemptsData.map((_, index) => `Attempt ${index + 1}`);
    const scores = attemptsData.map(attempt => attempt.score);
    const accuracy = attemptsData.map(attempt => attempt.stats.accuracy * 100);
    
    // Create chart
    if (window.progressChart) {
        try {
            window.progressChart.destroy();
        } catch (error) {
            console.error('Error destroying previous chart:', error);
        }
    }
    
    window.progressChart = new Chart(canvas, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Score',
                    data: scores,
                    borderColor: 'rgba(99, 132, 255, 1)',
                    backgroundColor: 'rgba(99, 132, 255, 0.1)',
                    borderWidth: 2,
                    tension: 0.3,
                    yAxisID: 'y'
                },
                {
                    label: 'Accuracy (%)',
                    data: accuracy,
                    borderColor: 'rgba(75, 192, 128, 1)',
                    backgroundColor: 'rgba(75, 192, 128, 0.1)',
                    borderWidth: 2,
                    tension: 0.3,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: 'rgba(255, 255, 255, 0.7)'
                    }
                },
                y: {
                    position: 'left',
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Score',
                        color: 'rgba(255, 255, 255, 0.7)'
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: 'rgba(255, 255, 255, 0.7)'
                    }
                },
                y1: {
                    position: 'right',
                    beginAtZero: true,
                    max: 100,
                    title: {
                        display: true,
                        text: 'Accuracy (%)',
                        color: 'rgba(255, 255, 255, 0.7)'
                    },
                    grid: {
                        drawOnChartArea: false,
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
                    callbacks: {
                        label: function(context) {
                            const label = context.dataset.label || '';
                            const value = context.parsed.y;
                            return `${label}: ${value.toFixed(1)}`;
                        }
                    }
                }
            }
        }
    });
}
