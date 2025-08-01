document.addEventListener('DOMContentLoaded', function () {

    // Destroy all heatmap days after today
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    document.querySelectorAll('.heatmap-day').forEach(day => {
        const dateStr = day.getAttribute('data-date');
        if (dateStr) {
            const cellDate = new Date(dateStr);
            cellDate.setHours(0, 0, 0, 0);
            if (cellDate > today) {
                day.style.display = 'none'; // or: day.remove();
            }
        }
    });
    // Day progress circle
    function updateDayProgress() {
        const now = new Date();
        const endOfDay = new Date();
        endOfDay.setHours(23, 59, 59, 999);

        const totalMs = 24 * 60 * 60 * 1000; // Total milliseconds in a day
        const elapsedMs = now.getTime() - new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
        const remainingMs = totalMs - elapsedMs;

        // Calculate progress percentage (0-100)
        const progressPercent = (elapsedMs / totalMs) * 100;
        const progressAngle = (progressPercent / 100) * 360;

        // Calculate remaining time
        const remainingHours = Math.floor(remainingMs / (1000 * 60 * 60));
        const remainingMinutes = Math.floor((remainingMs % (1000 * 60 * 60)) / (1000 * 60));

        // Update the circle
        const circle = document.getElementById('dayProgress');
        const timeDisplay = document.getElementById('progressTime');

        if (circle && timeDisplay) {
            circle.style.setProperty('--progress-angle', progressAngle + 'deg');
            timeDisplay.textContent = `${remainingHours.toString().padStart(2, '0')}:${remainingMinutes.toString().padStart(2, '0')}`;
        }
    }

    // Update immediately and then every minute
    updateDayProgress();
    setInterval(updateDayProgress, 60000);

    // Heatmap tooltip functionality
    const tooltip = document.getElementById('heatmap-tooltip');
    const heatmapDays = document.querySelectorAll('.heatmap-day');

    heatmapDays.forEach(day => {
        day.addEventListener('mouseenter', function (e) {
            const date = this.getAttribute('data-date');
            const count = parseInt(this.getAttribute('data-count'));
            const formattedDate = new Date(date).toLocaleDateString('en-US', {
                weekday: 'long',
                month: 'short',
                day: 'numeric',
                year: 'numeric'
            });

            let activityText;
            if (count === 0) {
                activityText = 'No activities';
            } else if (count === 1) {
                activityText = '1 activity';
            } else {
                activityText = `${count} activities`;
            }

            tooltip.innerHTML = `<strong>${activityText}</strong><br>${formattedDate}`;
            tooltip.style.display = 'block';

            // Position tooltip above the hovered day
            const rect = this.getBoundingClientRect();
            const tooltipRect = tooltip.getBoundingClientRect();

            let left = rect.left + (rect.width / 2) - (tooltipRect.width / 2);
            let top = rect.top - tooltipRect.height - 12;

            // Keep tooltip within viewport bounds
            const padding = 10;
            if (left < padding) {
                left = padding;
            } else if (left + tooltipRect.width > window.innerWidth - padding) {
                left = window.innerWidth - tooltipRect.width - padding;
            }

            if (top < padding) {
                top = rect.bottom + 12;
            }

            tooltip.style.left = left + window.scrollX + 'px';
            tooltip.style.top = top + window.scrollY + 'px';
        });

        day.addEventListener('mouseleave', function () {
            tooltip.style.display = 'none';
        });
    });

        // Doughnut charts for exam progress on profile page
        document.querySelectorAll('.exam-chart-card canvas').forEach(canvas => {
            console.log('Initializing doughnut chart for canvas:', canvas.dataset);
            let labels = canvas.dataset.labels;
            // split from string to array
            labels = labels.split(',');
            const solvedData = JSON.parse(canvas.dataset.solved);
            const totalData = JSON.parse(canvas.dataset.total);

            new Chart(canvas.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                label: 'Solved',
                data: solvedData,
                backgroundColor: [
                    'rgba(107, 138, 253, 0.8)',
                    'rgba(34, 197, 94, 0.8)',
                    'rgba(239, 68, 68, 0.8)',
                    'rgba(234, 179, 8, 0.8)',
                ],
                borderWidth: 0,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                    boxWidth: 12,
                    padding: 15,
                    color: 'white'
                    }
                },
                tooltip: {
                    callbacks: {
                    label: function(context) {
                        const label = context.label || '';
                        const solved = context.raw;
                        const total = totalData[context.dataIndex];
                        const percentage = total > 0 ? (solved / total * 100).toFixed(1) : 0;
                        return `${label}: ${solved} / ${total} (${percentage}%)`;
                    }
                    }
                }
                },
                cutout: '60%'
            }
            });
        });

    // Modal functionality
    const activityModal = document.getElementById('activity-modal');
    const testsModal = document.getElementById('tests-modal');

    // Activity modal
    const viewAllActivityBtn = document.getElementById('view-all-activity');
    if (viewAllActivityBtn) {
        viewAllActivityBtn.addEventListener('click', function () {
            activityModal.style.display = 'block';
        });
    }

    // Tests modal
    const viewAllTestsBtn = document.getElementById('view-all-tests');
    if (viewAllTestsBtn) {
        viewAllTestsBtn.addEventListener('click', function () {
            testsModal.style.display = 'block';
        });
    }

    // Close buttons
    const closeButtons = document.querySelectorAll('.modal-close');
    closeButtons.forEach(function (btn) {
        btn.addEventListener('click', function () {
            activityModal.style.display = 'none';
            testsModal.style.display = 'none';
        });
    });

    // Close modal when clicking outside
    window.addEventListener('click', function (event) {
        if (event.target === activityModal) {
            activityModal.style.display = 'none';
        }
        if (event.target === testsModal) {
            testsModal.style.display = 'none';
        }
    });
    function isTodayExtended() {
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const yyyy = today.getFullYear();
        const mm = String(today.getMonth() + 1).padStart(2, '0');
        const dd = String(today.getDate()).padStart(2, '0');
        const todayStr = `${yyyy}-${mm}-${dd}`;

        // If we already checked and stored the result, use it
        if (window.todayExtendedChecked !== undefined) {
            return window.todayExtendedChecked;
        }
        
        // If we have a server-rendered flag available, use that
        const streakExtendedToday = document.getElementById('streak-extended-today');
        if (streakExtendedToday) {
            const isExtended = streakExtendedToday.value === 'true';
            window.todayExtendedChecked = isExtended;
            return isExtended;
        }
        
        // Default to using the heatmap cell count as a fallback
        const todayCell = document.querySelector(`.heatmap-day[data-date="${todayStr}"]`);
        if (todayCell) {
            // We can only estimate based on activity count
            // This is less accurate but will work without backend changes
            const count = parseInt(todayCell.getAttribute('data-count'), 10);
            window.todayExtendedChecked = count > 0;
            return count > 0;
        }
        
        return false;
    }

    // Add an API call to check daily task status more accurately
    // You can call this early in your page load
    function checkDailyTaskStatus() {
        fetch('/api/daily-task/status')
            .then(response => response.json())
            .then(data => {
                window.todayExtendedChecked = data.completed_today;
                // Update UI after getting the accurate data
                updateStreakUI();
            })
            .catch(error => {
                console.error('Error checking daily task status:', error);
            });
    }

    // Update the streak UI based on extension status
    function updateStreakUI() {
        const extendedDiv = document.getElementById('extended');
        const notExtendedDiv = document.getElementById('not-extended');
        const extendButton = document.querySelector('.extend');
        const practiceButton = document.getElementById('practice-button');
        
        const isExtended = isTodayExtended();
        
        if (isExtended) {
            if (extendedDiv) extendedDiv.style.display = '';
            if (notExtendedDiv) notExtendedDiv.style.display = 'none';
        } else {
            if (extendedDiv) extendedDiv.style.display = 'none';
            if (notExtendedDiv) notExtendedDiv.style.display = '';
        }
    }

    // Call this early in your page load
    checkDailyTaskStatus();

    // Daily task modal functionality
    const extendStreakModal = document.getElementById('extend-streak-modal');
    const extendButton = document.querySelector('.extend');
    const practiceButton = document.getElementById('practice-button');

    // Show modal when extend button is clicked
    if (extendButton) {
        extendButton.addEventListener('click', function () {
            document.querySelector('#extend-streak-modal .modal-header h3').innerHTML = '<i class="fas fa-calendar-plus"></i> Daily Task';
            extendStreakModal.style.display = 'block';
            // Fetch exams when modal is opened
            fetchExams();
        });
    }

    // Show modal when practice button is clicked
    if (practiceButton) {
        practiceButton.addEventListener('click', function () {
            document.querySelector('#extend-streak-modal .modal-header h3').innerHTML = '<i class="fas fa-dumbbell"></i> Practice Session';
            extendStreakModal.style.display = 'block';
            // Fetch exams when modal is opened
            fetchExams();
        });
    }

    // Close extend streak modal with X or clicking outside
    document.querySelectorAll('#extend-streak-modal .modal-close').forEach(closeBtn => {
        closeBtn.addEventListener('click', () => {
            extendStreakModal.style.display = 'none';
        });
    });

    window.addEventListener('click', function (event) {
        if (event.target === extendStreakModal) {
            extendStreakModal.style.display = 'none';
        }
    });

    // Filter logic for Exam, Subject and Chapter dropdowns
    const examFilter = document.getElementById('examFilter');
    const subjectFilter = document.getElementById('subjectFilter');
    const chapterFilter = document.getElementById('chapterFilter');

    // Fetch exams from API instead of using server-rendered data
    function fetchExams() {
        return new Promise((resolve, reject) => {
            // Show loading state
            const examFilter = document.getElementById('examFilter');
            examFilter.innerHTML = '<option value="">Loading...</option>';

            fetch('/api/exams')
                .then(response => response.json())
                .then(data => {
                    let options = '<option value="">Select Exam</option>';
                    if (data.exams && Array.isArray(data.exams)) {
                        data.exams.forEach(exam => {
                            options += `<option value="${exam._id}">${exam.name}</option>`;
                        });
                    }
                    examFilter.innerHTML = options;
                    resolve();
                })
                .catch(error => {
                    console.error('Error fetching exams:', error);
                    examFilter.innerHTML = '<option value="">Error loading exams</option>';
                    reject(error);
                });
        });
    }

    examFilter.addEventListener('change', function () {
        const examId = this.value;

        // Reset dependent filters
        subjectFilter.innerHTML = '<option value="">Select Subject</option>';
        chapterFilter.innerHTML = '<option value="">Select Chapter</option>';

        if (examId) {
            // Enable subject filter and fetch subjects using API
            subjectFilter.disabled = false;
            fetchSubjects(examId);
        } else {
            subjectFilter.disabled = true;
            chapterFilter.disabled = true;
        }
    });

    subjectFilter.addEventListener('change', function () {
        const subjectId = this.value;
        const examId = examFilter.value;

        // Reset chapter filter
        chapterFilter.innerHTML = '<option value="">Select Chapter</option>';

        if (subjectId && examId) {
            // Enable chapter filter and fetch chapters
            chapterFilter.disabled = false;
            fetchChapters(examId, subjectId);
        } else {
            chapterFilter.disabled = true;
        }
    });

    // Add new event listener for chapter selection to fetch SR data
    chapterFilter.addEventListener('change', function () {
        const chapterId = this.value;
        const warningDiv = document.getElementById('thresholdWarning');
        
        if (chapterId) {
            fetchSRData(chapterId);
        } else {
            // Reset to default values if no chapter selected
            document.getElementById('questionCount').value = 5;
            document.getElementById('timeLimit').value = 30;
            if (warningDiv) {
                warningDiv.style.display = 'none';
            }
        }
    });

    // Add event listener to question count input to check threshold
    document.getElementById('questionCount').addEventListener('input', function() {
        checkQuestionThreshold();
    });

    // Add event listeners to the number input buttons
    document.addEventListener('click', function(e) {
        if (e.target.matches('.number-input button')) {
            // Small delay to ensure the input value has been updated
            setTimeout(checkQuestionThreshold, 10);
        }
    });

    // Also listen for change events on the question count input
    document.getElementById('questionCount').addEventListener('change', function() {
        checkQuestionThreshold();
    });

    function fetchSRData(chapterId) {
        fetch(`/api/practice/sr/${chapterId}`).then(response => response.json()).then(data => {
                const questionCountInput = document.getElementById('questionCount');
                const timeLimitInput = document.getElementById('timeLimit');
                
                questionCountInput.value = data.questions;
                timeLimitInput.value = Math.ceil(data.time / 60000); // Convert ms to minutes
                
                // Store the threshold for warning checks
                questionCountInput.dataset.threshold = data.questions;
                
                // Check if current value is below threshold
                checkQuestionThreshold();
            })
            .catch(error => {
                console.error('Error fetching SR data:', error);
                // Fall back to defaults
                document.getElementById('questionCount').value = 5;
                document.getElementById('timeLimit').value = 30;
            });
    }

    function checkQuestionThreshold() {
        const questionCountInput = document.getElementById('questionCount');
        const warningDiv = document.getElementById('thresholdWarning');
        
        if (!questionCountInput || !warningDiv) return;
        
        const threshold = parseInt(questionCountInput.dataset.threshold);
        const currentValue = parseInt(questionCountInput.value);
        
        // Only show warning if we have a threshold set and current value is below it
        if (threshold && !isNaN(threshold) && !isNaN(currentValue) && currentValue < threshold) {
            warningDiv.style.display = 'block';
            warningDiv.innerHTML = `
                <i class="fas fa-exclamation-triangle"></i>
                <span>Warning: Questions below ${threshold} won't count as a revision for this chapter.</span>
            `;
        } else {
            warningDiv.style.display = 'none';
        }
    }

    function fetchSubjects(examId) {
        // Show loading state
        subjectFilter.innerHTML = '<option value="">Loading...</option>';

        // Use the API endpoint from api.py instead of search/filters
        fetch(`/api/exams/${examId}/subjects?full=true`)
            .then(response => response.json())
            .then(data => {
                let options = '<option value="">Select Subject</option>';
                if (data.subjects && Array.isArray(data.subjects)) {
                    data.subjects.forEach(subject => {
                        options += `<option value="${subject._id}">${subject.name}</option>`;
                    });
                }
                subjectFilter.innerHTML = options;
            })
            .catch(error => {
                console.error('Error fetching subjects:', error);
                subjectFilter.innerHTML = '<option value="">Error loading subjects</option>';
            });
    }

    function fetchChapters(examId, subjectId) {
        // Show loading state
        chapterFilter.innerHTML = '<option value="">Loading...</option>';

        // For chapters, we need to keep using the existing endpoint as api.py doesn't 
        // have a direct endpoint for chapters of a subject
        fetch(`/search/filters?examId=${examId}&subjectId=${subjectId}`)
            .then(response => response.json())
            .then(data => {
                let options = '<option value="">Select Chapter</option>';
                if (Array.isArray(data)) {
                    data.forEach(chapter => {
                        options += `<option value="${chapter._id}">${chapter.name}</option>`;
                    });
                }
                chapterFilter.innerHTML = options;
            })
            .catch(error => {
                console.error('Error fetching chapters:', error);
                chapterFilter.innerHTML = '<option value="">Error loading chapters</option>';
            });
    }

    // Start daily task functionality
    document.getElementById('startDailyTask').addEventListener('click', function () {
        const examId = examFilter.value;
        const subjectId = subjectFilter.value;
        const chapterId = chapterFilter.value;
        const questionCount = document.getElementById('questionCount').value;
        const timeLimit = document.getElementById('timeLimit').value;

        if (!examId) {
            alert('Please select an exam');
            return;
        }

        if (!subjectId) {
            alert('Please select a subject');
            return;
        }

        // Create URL with params
        const url = `/practice/generate?exam=${examId}&subject=${subjectId}${chapterId ? '&chapter=' + chapterId : ''}&count=${questionCount}&time=${timeLimit}`;

        // Navigate to the daily task
        window.location.href = url;
    });

    // Activity pagination
    if (activityModal) {
        activityModal.addEventListener('click', function(event) {
            // Check if clicked element is a pagination button
            const paginationBtn = event.target.closest('.pagination-btn:not(.disabled):not(.active)');
            if (paginationBtn) {
                // Prevent default and stop propagation
                event.preventDefault();
                event.stopPropagation();
                
                const page = paginationBtn.getAttribute('data-page');
                if (page) {
                    loadActivityPage(page);
                }
            }
        });
    }
    
    // Fix for the loadActivityPage function to replace only the activity items
    function loadActivityPage(page) {
        // Show loading indicator only inside the activity list container
        const activityListContainer = activityModal.querySelector('.activity-list-full');
        
        if (activityListContainer) {
            // Only replace the activity list content, not the whole modal body
            activityListContainer.innerHTML = '<div class="loading-spinner"><i class="fas fa-circle-notch fa-spin"></i> Loading activities...</div>';
            
            // Fetch the new page
            fetch(`/api/activities?page=${page}&per_page=10`)
                .then(response => response.json())
                .then(data => {
                    // Update pagination info
                    const paginationInfo = activityModal.querySelector('.pagination-info');
                    if (paginationInfo) {
                        paginationInfo.textContent = `Showing ${(data.page - 1) * data.per_page + 1} to ${Math.min(data.page * data.per_page, data.total)} of ${data.total} activities`;
                    }
                    
                    // Update pagination buttons by completely replacing them
                    updatePaginationButtons(data.page, data.total_pages);
                    
                    // Render only the activity items
                    let activitiesHtml = '';
                    data.activities.forEach(item => {
                        activitiesHtml += renderActivityItem(item);
                    });
                    
                    // Replace only the activity list content
                    activityListContainer.innerHTML = activitiesHtml;
                })
                .catch(error => {
                    console.error('Error loading activities:', error);
                    activityListContainer.innerHTML = '<div class="error-message">Error loading activities. Please try again.</div>';
                });
        } else {
            // Fall back to replacing the whole modal body
            const modalBody = activityModal.querySelector('.modal-body');
            modalBody.innerHTML = '<div class="loading-spinner"><i class="fas fa-circle-notch fa-spin"></i> Loading activities...</div>';
            
            fetch(`/api/activities?page=${page}&per_page=10`)
                .then(response => response.json())
                .then(data => {
                    renderActivities(modalBody, data);
                })
                .catch(error => {
                    console.error('Error loading activities:', error);
                    modalBody.innerHTML = '<div class="error-message">Error loading activities. Please try again.</div>';
                });
        }
    }
    
    // Replace the entire updatePaginationButtons function with this improved version
    function updatePaginationButtons(currentPage, totalPages) {
        const paginationControls = activityModal.querySelector('.pagination-controls');
        if (!paginationControls) return;
        
        // Generate entirely new pagination HTML instead of trying to update existing buttons
        let paginationHtml = '';
        
        // First and previous buttons
        if (currentPage > 1) {
            paginationHtml += `
                <button class="pagination-btn" data-page="1">
                    <i class="fas fa-angle-double-left"></i>
                </button>
                <button class="pagination-btn" data-page="${currentPage - 1}">
                    <i class="fas fa-angle-left"></i>
                </button>`;
        } else {
            paginationHtml += `
                <button class="pagination-btn disabled">
                    <i class="fas fa-angle-double-left"></i>
                </button>
                <button class="pagination-btn disabled">
                    <i class="fas fa-angle-left"></i>
                </button>`;
        }
        
        // Page numbers with ellipses
        const pagesAroundCurrent = 2; // Show 2 pages before and after current
        let startPage = Math.max(currentPage - pagesAroundCurrent, 1);
        let endPage = Math.min(currentPage + pagesAroundCurrent, totalPages);
        
        // Always show first page
        if (startPage > 1) {
            paginationHtml += `<button class="pagination-btn" data-page="1">1</button>`;
            
            // Add ellipsis if there's a gap
            if (startPage > 2) {
                paginationHtml += `<span class="pagination-ellipsis">...</span>`;
            }
        }
        
        // Pages around current
        for (let i = startPage; i <= endPage; i++) {
            paginationHtml += `<button class="pagination-btn ${i === currentPage ? 'active' : ''}" data-page="${i}">${i}</button>`;
        }
        
        // Always show last page
        if (endPage < totalPages) {
            // Add ellipsis if there's a gap
            if (endPage < totalPages - 1) {
                paginationHtml += `<span class="pagination-ellipsis">...</span>`;
            }
            paginationHtml += `<button class="pagination-btn" data-page="${totalPages}">${totalPages}</button>`;
        }
        
        // Next and last buttons
        if (currentPage < totalPages) {
            paginationHtml += `
                <button class="pagination-btn" data-page="${currentPage + 1}">
                    <i class="fas fa-angle-right"></i>
                </button>
                <button class="pagination-btn" data-page="${totalPages}">
                    <i class="fas fa-angle-double-right"></i>
                </button>`;
        } else {
            paginationHtml += `
                <button class="pagination-btn disabled">
                    <i class="fas fa-angle-right"></i>
                </button>
                <button class="pagination-btn disabled">
                    <i class="fas fa-angle-double-right"></i>
                </button>`;
        }
        
        // Replace the entire pagination controls content
        paginationControls.innerHTML = paginationHtml;
    }
    
    function renderActivities(container, data) {
        // Create a new container for activities
        let html = '';
        
        if (data.activities && data.activities.length > 0) {
            html += '<div class="activity-list-full">';
            
            data.activities.forEach(item => {
                html += renderActivityItem(item);
            });
            
            html += '</div>';
            
            // Add pagination controls
            html += `
                <div class="pagination-container">
                    <div class="pagination-info">
                        Showing ${(data.page - 1) * data.per_page + 1} 
                        to ${Math.min(data.page * data.per_page, data.total)} 
                        of ${data.total} activities
                    </div>
                    <div class="pagination-controls">
                        ${data.page > 1 ? 
                            `<button class="pagination-btn" data-page="1">
                                <i class="fas fa-angle-double-left"></i>
                            </button>
                            <button class="pagination-btn" data-page="${data.page - 1}">
                                <i class="fas fa-angle-left"></i>
                            </button>` : 
                            `<button class="pagination-btn disabled">
                                <i class="fas fa-angle-double-left"></i>
                            </button>
                            <button class="pagination-btn disabled">
                                <i class="fas fa-angle-left"></i>
                            </button>`
                        }
                        
                        ${renderPaginationNumbers(data.page, data.total_pages)}
                        
                        ${data.page < data.total_pages ? 
                            `<button class="pagination-btn" data-page="${data.page + 1}">
                                <i class="fas fa-angle-right"></i>
                            </button>
                            <button class="pagination-btn" data-page="${data.total_pages}">
                                <i class="fas fa-angle-double-right"></i>
                            </button>` : 
                            `<button class="pagination-btn disabled">
                                <i class="fas fa-angle-right"></i>
                            </button>
                            <button class="pagination-btn disabled">
                                <i class="fas fa-angle-double-right"></i>
                            </button>`
                        }
                    </div>
                </div>`;
        } else {
            html = '<div class="empty-state"><p>No activity to show.</p></div>';
        }
        
        container.innerHTML = html;
    }
    
    // Update the renderPaginationNumbers function to include ellipsis and always show last page
    function renderPaginationNumbers(currentPage, totalPages) {
        let html = '';
        
        // Always show first page, last page, current page, and pages around current
        const showFirstPage = true;
        const showLastPage = true;
        const pagesAroundCurrent = 2; // Show 2 pages before and after current
        
        // Calculate the range of pages to show
        let startPage = Math.max(currentPage - pagesAroundCurrent, 1);
        let endPage = Math.min(currentPage + pagesAroundCurrent, totalPages);
        
        // Always show page 1
        if (showFirstPage && startPage > 1) {
            html += `<button class="pagination-btn" data-page="1">1</button>`;
            
            // Add ellipsis if there's a gap
            if (startPage > 2) {
                html += `<span class="pagination-ellipsis">...</span>`;
            }
        }
        
        // Show pages around current page
        for (let i = startPage; i <= endPage; i++) {
            html += `<button class="pagination-btn ${i === currentPage ? 'active' : ''}" 
                     data-page="${i}">${i}</button>`;
        }
        
        // Always show last page
        if (showLastPage && endPage < totalPages) {
            // Add ellipsis if there's a gap
            if (endPage < totalPages - 1) {
                html += `<span class="pagination-ellipsis">...</span>`;
            }
            
            html += `<button class="pagination-btn" data-page="${totalPages}">${totalPages}</button>`;
        }
        
        return html;
    }
    
    function renderActivityItem(item) {
        let iconHtml = '';
        let contentHtml = '';
        
        // Generate icon HTML
        switch(item.action) {
            case 'test_created':
                iconHtml = '<div class="activity-icon"><i class="fas fa-plus-circle"></i></div>';
                break;
            case 'test_completed':
                iconHtml = '<div class="activity-icon"><i class="fas fa-check-circle"></i></div>';
                break;
            case 'test_started':
                iconHtml = '<div class="activity-icon"><i class="fas fa-play-circle"></i></div>';
                break;
            case 'attempt_question':
                if (item.details.is_correct) {
                    iconHtml = '<div class="activity-icon correct"><i class="fas fa-check"></i></div>';
                } else {
                    iconHtml = '<div class="activity-icon incorrect"><i class="fas fa-times"></i></div>';
                }
                break;
            case 'practice_completed':
                if (item.details.is_success) {
                    iconHtml = '<div class="activity-icon correct"><i class="fas fa-fire"></i></div>';
                } else {
                    iconHtml = '<div class="activity-icon incorrect"><i class="fas fa-heart-broken"></i></div>';
                }
                break;
            case 'practice_started':
                iconHtml = '<div class="activity-icon"><i class="fas fa-play"></i></div>';
                break;
            default:
                iconHtml = '<div class="activity-icon"><i class="fas fa-bell"></i></div>';
        }
        
        // Generate content HTML based on action type
        switch(item.action) {
            case 'test_created':
                contentHtml = `<div class="activity-header">Created a new test:&nbsp; <strong>${item.details.title}</strong></div>`;
                break;
            case 'test_completed':
                contentHtml = `
                    <div class="activity-header">
                        Completed test:&nbsp; <strong>${item.details.title}</strong>
                        <div class="activity-score">${item.details.score}</div>
                    </div>`;
                break;
            case 'test_started':
                contentHtml = `<div class="activity-header">Started test:&nbsp; <strong>${item.details.title}</strong></div>`;
                break;
            case 'attempt_question':
                contentHtml = `
                    <div class="activity-header">
                        Attempted a question 
                        <div class="${item.details.is_correct ? 'answer-correct' : 'answer-incorrect'}">
                            <i class="fas fa-${item.details.is_correct ? 'check' : 'times'}-circle"></i> 
                            ${item.details.is_correct ? 'Correct' : 'Incorrect'}
                        </div>
                    </div>`;
                break;
            case 'daily_task_completed':
                contentHtml = `
                    <div class="activity-header">
                        <div class="activity-header-content">
                            <span>Completed daily task</span>
                            <div class="daily-task-stats">
                                <div class="daily-task-badge ${item.details.is_success ? 'success' : 'failed'}">
                                    <i class="fas fa-${item.details.is_success ? 'fire' : 'heart-broken'}"></i> 
                                    ${item.details.is_success ? 'Streak Extended' : 'Streak Broken'}
                                </div>
                                
                                <div class="health-badge ${
                                    item.details.health_remaining > 70 ? 'high' : 
                                    item.details.health_remaining > 30 ? 'medium' : 'low'
                                }">
                                    <i class="fas fa-heart"></i> ${Math.round(item.details.health_remaining)}%
                                </div>
                            </div>
                        </div>
                    </div>`;
                break;
            case 'practice_started':
                contentHtml = `
                    <div class="activity-header">
                        <div class="activity-header-content">
                            <span>Started practice session: <strong>${item.details.exam} - ${item.details.subject} - ${item.details.chapter}</strong></span>
                            <div class="daily-task-info">
                                <span class="task-badge">
                                    <i class="fas fa-list-ol"></i> ${item.details.count} questions
                                </span>
                            </div>
                        </div>
                    </div>`;
                break;
            default:
                contentHtml = `<div class="activity-header">${item.action}</div>`;
        }
        
        // Format timestamp
        let formattedDate = 'Unknown date';
        
        // Handle the MongoDB timestamp format correctly
        if (item.timestamp) {
            // Check if it's a string or number
            let timestamp;
            if (typeof item.timestamp === 'string') {
                timestamp = new Date(item.timestamp);
            } else if (typeof item.timestamp === 'number') {
                timestamp = new Date(item.timestamp);
            }
            
            // Only format if it's a valid date
            if (!isNaN(timestamp.getTime())) {
                formattedDate = timestamp.toLocaleString();
            }
        }
        
        return `
            <div class="activity-item">
                ${iconHtml}
                <div class="activity-content">
                    ${contentHtml}
                    <div class="activity-time">
                        <i class="far fa-clock"></i> ${formattedDate}
                    </div>
                </div>
            </div>
        `;
    }

    // Practice Chapter button functionality
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('practice-chapter-btn') || e.target.closest('.practice-chapter-btn')) {
            const btn = e.target.classList.contains('practice-chapter-btn') ? e.target : e.target.closest('.practice-chapter-btn');
            const chapterId = btn.getAttribute('data-chapter');
            const examName = btn.getAttribute('data-exam');
            const subjectName = btn.getAttribute('data-subject');
            
            if (chapterId) {
                // Find the exam and subject IDs from the practice modal
                // We'll need to open the modal and pre-select the options
                openPracticeModal(examName, subjectName, chapterId);
            }
        }
    });

    function openPracticeModal(examName, subjectName, chapterId) {
        const extendStreakModal = document.getElementById('extend-streak-modal');
        const modalTitle = document.querySelector('#extend-streak-modal .modal-header h3');
        
        // Update modal title
        modalTitle.innerHTML = '<i class="fas fa-brain"></i> Practice Chapter';
        
        // Show the modal
        extendStreakModal.style.display = 'block';
        
        // Fetch exams and pre-select the appropriate ones
        fetchExams().then(() => {
            // Try to find and select the exam
            const examSelect = document.getElementById('examFilter');
            for (let option of examSelect.options) {
                if (option.text === examName) {
                    examSelect.value = option.value;
                    examSelect.dispatchEvent(new Event('change'));
                    
                    // Wait a bit for subjects to load, then select subject
                    setTimeout(() => {
                        const subjectSelect = document.getElementById('subjectFilter');
                        for (let option of subjectSelect.options) {
                            if (option.text === subjectName) {
                                subjectSelect.value = option.value;
                                subjectSelect.dispatchEvent(new Event('change'));
                                
                                // Wait for chapters to load, then select chapter
                                setTimeout(() => {
                                    const chapterSelect = document.getElementById('chapterFilter');
                                    chapterSelect.value = chapterId;
                                    chapterSelect.dispatchEvent(new Event('change'));
                                }, 500);
                                break;
                            }
                        }
                    }, 500);
                    break;
                }
            }
        });
    }
});