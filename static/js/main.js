document.addEventListener('DOMContentLoaded', () => {
    const logInteractionForm = document.getElementById('logInteractionForm');
    const logMessage = document.getElementById('logMessage');

    if (logInteractionForm) {
        logInteractionForm.addEventListener('submit', async (event) => {
            event.preventDefault(); // Prevent default form submission

            const studentId = document.getElementById('studentId').value;
            const contentId = document.getElementById('contentSelect').value;
            const score = document.getElementById('score').value;
            const timeSpent = document.getElementById('timeSpent').value;
            const completed = document.getElementById('completed').checked;

            const data = {
                student_id: parseInt(studentId),
                content_id: parseInt(contentId),
                score: score ? parseInt(score) : null,
                time_spent_seconds: timeSpent ? parseInt(timeSpent) : null,
                completed: completed
            };

            try {
                const response = await fetch('/api/log_interaction', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(data),
                });

                const result = await response.json();

                if (response.ok) {
                    logMessage.textContent = result.message;
                    logMessage.style.color = 'green';
                    // Optionally, refresh part of the dashboard or clear form
                    setTimeout(() => {
                        window.location.reload(); // Simple reload for demo
                    }, 1000);
                } else {
                    logMessage.textContent = `Error: ${result.error || 'Failed to log interaction'}`;
                    logMessage.style.color = 'red';
                }
            } catch (error) {
                console.error('Error logging interaction:', error);
                logMessage.textContent = 'Network error or server unreachable.';
                logMessage.style.color = 'red';
            }
        });
    }
});