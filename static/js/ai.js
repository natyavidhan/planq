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
    const historyList = document.querySelector('.history-list');

    let chatHistory = [];

    // Function to load existing messages if any
    function loadExistingMessages() {
        const existingMessages = document.querySelectorAll('.message');
        existingMessages.forEach(msg => {
            const role = msg.classList.contains('user') ? 'user' : 'model';
            const contentEl = msg.querySelector('.message-content p');
            if (role && contentEl) {
                const content = contentEl.innerText;
                chatHistory.push({ role, content });
            }
        });
        //  render markdown for existing messages
        existingMessages.forEach(msg => {
            const messageContent = msg.querySelector('.message-content');
            if (messageContent) {
                const p = messageContent.querySelector('p');
                if (p) {
                    const text = p.innerHTML
                    const html = marked.parse(text);
                    messageContent.innerHTML = html;
                }
            }
        });
    }

    function fetchAndPopulateSubjects(examId, subjectToSelect = null) {
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
                        subjectSelect.disabled = false; // Enable for user selection
                        
                        if (subjectToSelect) {
                            subjectSelect.value = subjectToSelect;
                            subjectSelect.disabled = true; // Disable if pre-selected
                        }
                    }
                })
                .catch(error => console.error('Error fetching subjects:', error));
        }
    }

    function initializeChatContext() {
        const examId = examSelect.dataset.examId;
        const subjectId = examSelect.dataset.subjectId;

        if (examId) {
            examSelect.value = examId;
            fetchAndPopulateSubjects(examId, subjectId);
        }
    }
    
    loadExistingMessages();
    initializeChatContext();

    // Handle exam selection to populate subjects
    examSelect.addEventListener('change', function () {
        const examId = this.value;
        fetchAndPopulateSubjects(examId);
    });

    // Handle chat deletion
    if (historyList) {
        historyList.addEventListener('click', function(event) {
            const deleteButton = event.target.closest('.delete-chat-btn');
            if (!deleteButton) return;

            event.preventDefault();
            event.stopPropagation();

            const chatIdToDelete = deleteButton.dataset.chatId;
            const chatItem = deleteButton.closest('.history-item');

            if (confirm('Are you sure you want to delete this chat?')) {
                fetch(`/ai/delete/${chatIdToDelete}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        chatItem.remove();
                        // If the deleted chat is the current one, redirect to new chat
                        const currentChatId = chatIdInput.value;
                        if (chatIdToDelete === currentChatId) {
                            window.location.href = '/ai';
                        }
                    } else {
                        alert('Failed to delete chat.');
                    }
                })
                .catch(error => {
                    console.error('Error deleting chat:', error);
                    alert('An error occurred while deleting the chat.');
                });
            }
        });
    }

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

        const examId = examSelect.value;
        const subjectId = subjectSelect.value;
        if (!examId || !subjectId) {
            const errorDiv = document.getElementById('chat-validation-error');
            errorDiv.textContent = 'Please select an exam and a subject before asking a question.';
            errorDiv.classList.add('active');
            setTimeout(() => {
                errorDiv.classList.remove('active');
            }, 3000);
            return;
        }

        // Hide welcome message if it's visible
        if (welcomeMessage) {
            welcomeMessage.style.display = 'none';
        }

        // Display user message
        appendMessage('user', query);
        chatInput.value = '';
        chatHistory.push({ role: 'user', content: query });

        // Get selected exam and subject
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
            updateLastMessage('ai', data.answer, data.context_used);
            chatHistory.push({ role: 'model', content: data.answer, context: data.context_used });
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
            <div class="message-container">
                <div class="message-content ${thinkingClass}">
                    <p>${messageText.replace(/\n/g, "<br>")}</p>
                </div>
            </div>
        `;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function updateLastMessage(sender, text, context = null) {
        const lastMessage = chatMessages.querySelector('.message:last-child');
        if (!lastMessage) return;
        
        const messageContainer = lastMessage.querySelector('.message-container');
        const messageContent = messageContainer ? messageContainer.querySelector('.message-content') : null;

        if (messageContent && messageContent.classList.contains('thinking')) {
            messageContent.classList.remove('thinking');
            messageContent.innerHTML = `<p>${text}</p>`;
            if (window.MathJax) {
                MathJax.typesetPromise && MathJax.typesetPromise().catch(err => console.error('MathJax error:', err));
            }
            let content = messageContent.querySelector('p');
            if (content) {
                const text = content.innerHTML;
                const html = marked.parse(text);
                messageContent.innerHTML = html;
            }

            if (context && context.length > 0) {
                const contextContainer = document.createElement('div');
                contextContainer.className = 'context-container';

                let contextGridHTML = '';
                context.forEach(item => {
                    const score = Math.round(item.score * 100);
                    const truncatedQuestion = item.question.length > 100 ? item.question.substring(0, 100) + '...' : item.question;

                    contextGridHTML += `
                        <a href="/question/${item._id}" target="_blank" class="context-item">
                            <p class="context-question">${truncatedQuestion}</p>
                            <div class="context-score">
                                <i class="fas fa-bolt"></i> ${score}% match
                            </div>
                        </a>
                    `;
                });

                contextContainer.innerHTML = `
                    <h4 class="context-title">
                        <i class="fas fa-book-open"></i> Context Used
                    </h4>
                    <div class="context-grid">
                        ${contextGridHTML}
                    </div>
                `;
                messageContainer.appendChild(contextContainer);
            }
        } else {
            appendMessage(sender, text);
        }
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
});
