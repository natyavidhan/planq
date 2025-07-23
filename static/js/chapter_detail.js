document.addEventListener('DOMContentLoaded', function() {
    if (window.MathJax) {
       MathJax.typesetPromise && MathJax.typesetPromise().catch(err => console.error('MathJax error:', err));
    }

    // Chart data is now passed via a script tag in the HTML
    if (typeof chapterData === 'undefined' || !chapterData.attempts) {
        return;
    }

    const { attempts, sr_data, ch_data } = chapterData;
    // Sort attempts by timestamp
    const allAttempts = attempts.map(attempt => ({
        ...attempt,
        timestamp: new Date(attempt.timestamp)
    })).sort((a, b) => a.timestamp - b.timestamp);

    // Group attempts by day to calculate daily stats
    const dailyStats = {};
    allAttempts.forEach(attempt => {
        const date = attempt.timestamp.toISOString().split('T')[0]; // YYYY-MM-DD
        if (!dailyStats[date]) {
            dailyStats[date] = {
                correct: 0,
                total: 0,
                totalTime: 0,
            };
        }
        dailyStats[date].total++;
        dailyStats[date].totalTime += attempt.time_taken;
        if (attempt.is_correct) {
            dailyStats[date].correct++;
        }
    });

    // Prepare data for charts
    const dailyAccuracyData = [];
    const dailyTimeData = [];
    const sortedDates = Object.keys(dailyStats).sort();

    sortedDates.forEach(date => {
        const stats = dailyStats[date];
        const avgAccuracy = (stats.correct / stats.total) * 100;
        const avgTime = (stats.totalTime / stats.total) / 1000; // in seconds

        dailyAccuracyData.push({ x: new Date(date), y: avgAccuracy });
        dailyTimeData.push({ x: new Date(date), y: avgTime });
    });

    // Progress Over Time Chart (Daily Average Accuracy)
    const progressCtx = document.getElementById('progressChart');
    if (progressCtx) {
        new Chart(progressCtx.getContext('2d'), {
            type: 'line',
            data: {
                datasets: [{
                    label: 'Daily Average Accuracy %',
                    data: dailyAccuracyData,
                    borderColor: 'rgb(107, 138, 253)',
                    backgroundColor: 'rgba(107, 138, 253, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { type: 'time', time: { unit: 'day', displayFormats: { day: 'MMM dd' } }, title: { display: true, text: 'Date' } },
                    y: { beginAtZero: true, max: 100, title: { display: true, text: 'Avg. Accuracy (%)' } }
                },
                plugins: { 
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (context) => `Avg. Accuracy: ${context.parsed.y.toFixed(1)}%`
                        }
                    }
                }
            }
        });
    }

    // Time Performance Chart (Daily Average Time)
    const timeCtx = document.getElementById('timeChart');
    if (timeCtx) {
        new Chart(timeCtx.getContext('2d'), {
            type: 'line',
            data: {
                datasets: [{
                    label: 'Daily Average Time (s)',
                    data: dailyTimeData,
                    borderColor: 'rgb(34, 197, 94)',
                    backgroundColor: 'rgba(34, 197, 94, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { type: 'time', time: { unit: 'day', displayFormats: { day: 'MMM dd' } }, title: { display: true, text: 'Date' } },
                    y: { beginAtZero: true, title: { display: true, text: 'Avg. Time (seconds)' } }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (context) => `Avg. Time: ${context.parsed.y.toFixed(1)}s`
                        }
                    }
                }
            }
        });
    }

    // Retention Chart
    const retentionCtx = document.getElementById('retentionChart');
    if (retentionCtx && sr_data && ch_data) {
        const lastRevision = new Date(sr_data.last_revision);
        const interval = sr_data.interval;
        const decayRate = ch_data.dr;
        const today = new Date();
        
        const retentionData = [];
        for (let i = 0; i <= interval; i++) {
            const date = new Date(lastRevision);
            date.setDate(date.getDate() + i);
            const retention = Math.exp((-decayRate * i) / interval) * 100;
            retentionData.push({ x: date, y: Math.max(0, retention) });
        }
        
        const daysSinceRevision = (today.getTime() - lastRevision.getTime()) / (1000 * 60 * 60 * 24);
        const todayRetention = Math.exp((-decayRate * daysSinceRevision) / interval) * 100;
        
        const todayData = [];
        if (daysSinceRevision >= 0 && daysSinceRevision <= interval) {
            todayData.push({ x: today, y: todayRetention });
        }

        new Chart(retentionCtx.getContext('2d'), {
            type: 'line',
            data: {
                datasets: [{
                    label: 'Memory Retention %',
                    data: retentionData,
                    borderColor: 'rgb(107, 138, 253)',
                    backgroundColor: 'rgba(107, 138, 253, 0.1)',
                    tension: 0.4,
                    fill: true,
                    pointRadius: 0,
                    pointHoverRadius: 0
                }, {
                    label: "Today's Retention",
                    data: todayData,
                    borderColor: 'rgb(239, 68, 68)',
                    backgroundColor: 'rgb(239, 68, 68)',
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    showLine: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { type: 'time', time: { unit: 'day', displayFormats: { day: 'MMM dd' } }, title: { display: false }, grid: { display: false } },
                    y: { beginAtZero: true, max: 100, title: { display: false }, ticks: { callback: (value) => value + '%' } }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (context) => context.datasetIndex === 1 ? `Today's Retention: ${context.parsed.y.toFixed(1)}%` : `Est. Retention: ${context.parsed.y.toFixed(1)}%`
                        }
                    }
                }
            }
        });
    }
});
