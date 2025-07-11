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
        
        const isExtended = isTodayExtended();
        
        if (isExtended) {
            if (extendedDiv) extendedDiv.style.display = '';
            if (notExtendedDiv) notExtendedDiv.style.display = 'none';
            if (extendButton) extendButton.style.display = 'none';
        } else {
            if (extendedDiv) extendedDiv.style.display = 'none';
            if (notExtendedDiv) notExtendedDiv.style.display = '';
            if (extendButton) extendButton.style.display = '';
        }
    }

    // Call this early in your page load
    checkDailyTaskStatus();

    // Daily task modal functionality
    const extendStreakModal = document.getElementById('extend-streak-modal');
    const extendButton = document.querySelector('.extend'); // Define extendButton here

    // Show modal when extend button is clicked
    if (extendButton) {
        extendButton.addEventListener('click', function () {
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
        // Show loading state
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
            })
            .catch(error => {
                console.error('Error fetching exams:', error);
                examFilter.innerHTML = '<option value="">Error loading exams</option>';
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
        const url = `/daily-task/generate?exam=${examId}&subject=${subjectId}${chapterId ? '&chapter=' + chapterId : ''}&count=${questionCount}&time=${timeLimit}`;

        // Navigate to the daily task
        window.location.href = url;
    });
});