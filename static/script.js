function switchTab(tabName) {
  document.querySelectorAll('.tab-content').forEach(tab => tab.style.display = 'none');
  document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));

  document.getElementById(`${tabName}-tab`).style.display = 'block';
  document.querySelector(`[onclick="switchTab('${tabName}')"]`).classList.add('active');

  if (tabName === 'history') {
      loadHistory();
  }
}

function loadHistory() {
    fetch('/history')
        .then(response => response.json())
        .then(data => {
            const historyContainer = document.getElementById('history-container');
            historyContainer.innerHTML = data.map(item => `
                <div class="history-item">
                    <div><strong>Input:</strong> ${item.input}</div>
                    <div><strong>Response:</strong> ${item.response}</div>
                    <div><small>Time: ${new Date(item.timestamp).toLocaleString()}</small></div>
                </div>
            `).join('');
        })
        .catch(error => console.error('Error loading history:', error));
}

function sendMessage() {
  const userInput = document.getElementById("user-input").value;
  const saveHistory = document.getElementById("save-history").checked;

  if (!userInput.trim()) return;

  // Disable the send button
  document.getElementById("send-button").disabled = true;

  // Show progress bar
  document.getElementById("progress-bar").style.display = "block";
  document.getElementById("progress").style.width = "100%";

  document.getElementById("chat-box").innerHTML += `
      <div class="message sent">${userInput}</div>
  `;

  // Clear the input box
  document.getElementById("user-input").value = "";

  fetch("/chat", {
      method: "POST",
      headers: {
          "Content-Type": "application/json",
      },
      body: JSON.stringify({ 
          message: userInput,
          save_history: saveHistory
      }),
  })
  .then((response) => response.json())
  .then((data) => {
      let chatbox = document.getElementById("chat-box");
      chatbox.innerHTML += `
          <div class="message received">${data.response.output}</div>
      `;
      chatbox.scrollTop = chatbox.scrollHeight;

      // Enable the send button
      document.getElementById("send-button").disabled = false;

      // Hide progress bar
      document.getElementById("progress-bar").style.display = "none";
      document.getElementById("progress").style.width = "0%";
  })
  .catch((error) => {
      console.error("Error:", error);
      document.getElementById("send-button").disabled = false;
  });
}

function clearHistory() {
    if (confirm('Are you sure you want to clear all chat history?')) {
        fetch('/clear-history', {
            method: 'POST',
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const historyContainer = document.getElementById('history-container');
                historyContainer.innerHTML = '';
            } else {
                alert('Failed to clear history');
            }
        })
        .catch(error => console.error('Error clearing history:', error));
    }
}