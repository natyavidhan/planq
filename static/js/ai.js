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
    const chatIdInput = document.getElementById('chat-id');

    let chatHistory = [];

    // Function to load existing messages if any
    function loadExistingMessages() {
        const existingMessages = document.querySelectorAll('.message');
        existingMessages.forEach(msg => {
            const role = msg.classList.contains('user') ? 'user' : 'model';
            const content = msg.querySelector('.message-content p').innerText;
            if (role && content) {
                chatHistory.push({ role, content });
            }
        });
    }
    
    loadExistingMessages();

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
        chatHistory.push({ role: 'user', content: query });

        // Get selected exam and subject
        const examId = examSelect.value;
        const subjectId = subjectSelect.value;
        const chatId = chatIdInput.value;

        // Show loading/thinking indicator for AI
        appendMessage('ai', 'Thinking...', true);

        // Send data to backend
        fetch('/ai/retrieve', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                query, 
                exam_id: examId, 
                subject_id: subjectId,
                chat_id: chatId,
                messages: chatHistory.slice(0, -1) // Send history without the current query
            })
        })
        .then(response => response.json())
        .then(data => {
            updateLastMessage('ai', data.answer);
            chatHistory.push({ role: 'model', content: data.answer });
        })
        .catch(error => {
            console.error('Error:', error);
            const errorMsg = 'Sorry, something went wrong. Please try again.';
            updateLastMessage('ai', errorMsg);
            chatHistory.push({ role: 'model', content: errorMsg });
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
            // Replace newline characters with <br> tags for proper rendering
            lastMessage.querySelector('p').innerHTML = text.replace(/\n/g, '<br>');
        } else {
            appendMessage(sender, text);
        }
        chatMessages.scrollTop = chatMessages.scrollHeight;
        if (window.MathJax) {
            MathJax.typesetPromise && MathJax.typesetPromise().catch(err => console.error('MathJax error:', err));
        }
    }
});
