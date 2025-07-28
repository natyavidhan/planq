document.addEventListener('DOMContentLoaded', function () {
    const chatForm = document.getElementById('ai-form');
    const chatInput = document.getElementById('chat-input');
    const chatMessages = document.getElementById('chat-messages');
    const welcomeMessage = document.querySelector('.welcome-message');
    const examSelect = document.getElementById('exam-select');
    const subjectSelect = document.getElementById('subject-select');
    const promptSuggestions = document.querySelectorAll('.suggestion-item');
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const chatSidebar = document.querySelector('.chat-sidebar');
    const chatOverlay = document.getElementById('chat-overlay');

    // Handle exam selection to populate subjects
    examSelect.addEventListener('change', function () {
        const examId = this.value;
        subjectSelect.innerHTML = '<option value="">Select Subject</option>';
        subjectSelect.disabled = true;

        if (examId) {
            fetch(`/api/exams/${examId}/subjects`)
                .then(response => response.json())
                .then(data => {
                    if (data.subjects && data.subjects.length > 0) {
                        data.subjects.forEach(subject => {
                            const option = document.createElement('option');
                            option.value = subject._id;
                            option.textContent = subject.name;
                            subjectSelect.appendChild(option);
                        });
                        subjectSelect.disabled = false;
                    }
                })
                .catch(error => console.error('Error fetching subjects:', error));
        }
    });

    // Handle prompt suggestion clicks
    promptSuggestions.forEach(item => {
        item.addEventListener('click', function() {
            const promptText = this.dataset.prompt;
            chatInput.value = promptText;
            chatInput.focus();
            // Optionally, submit the form right away
            // chatForm.requestSubmit();
        });
    });

    // Sidebar toggle for mobile
    if (sidebarToggle && chatSidebar) {
        sidebarToggle.addEventListener('click', function() {
            chatSidebar.classList.toggle('active');
            chatOverlay.classList.toggle('active');
        });

        chatOverlay.addEventListener('click', function() {
            chatSidebar.classList.remove('active');
            chatOverlay.classList.remove('active');
        });
    }

    // Handle form submission
    chatForm.addEventListener('submit', function (event) {
        event.preventDefault();
        const query = chatInput.value.trim();
        if (!query) return;

        // Hide welcome message if it's visible
        if (welcomeMessage) {
            welcomeMessage.style.display = 'none';
        }

        // Display user message
        appendMessage('user', query);
        chatInput.value = '';

        // Get selected exam and subject
        const examId = examSelect.value;
        const subjectId = subjectSelect.value;

        // Show loading/thinking indicator for AI
        appendMessage('ai', 'Thinking...', true);

        // Send data to backend
        fetch('/ai/retrieve', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ query, exam_id: examId, subject_id: subjectId })
        })
        .then(response => response.json())
        .then(data => {
            updateLastMessage('ai', data.answer);
        })
        .catch(error => {
            console.error('Error:', error);
            updateLastMessage('ai', 'Sorry, something went wrong. Please try again.');
        });
    });

    function appendMessage(sender, text, isThinking = false) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', sender);

        let thinkingClass = isThinking ? 'thinking' : '';
        let messageText = isThinking ? 'Thinking' : text;

        messageDiv.innerHTML = `
            <div class="message-avatar">
                <i class="fas fa-${sender === 'user' ? 'user' : 'robot'}"></i>
            </div>
            <div class="message-content ${thinkingClass}">
                <p>${messageText}</p>
            </div>
        `;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function updateLastMessage(sender, text) {
        const lastMessage = chatMessages.querySelector('.message:last-child .message-content');
        if (lastMessage && lastMessage.classList.contains('thinking')) {
            lastMessage.classList.remove('thinking');
            lastMessage.querySelector('p').innerHTML = text; // Use innerHTML to render markdown
        } else {
            appendMessage(sender, text);
        }
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
});
