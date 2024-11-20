function sendMessage() {
  const userInput = document.getElementById("user-input").value;

  // Disable the send button
  document.getElementById("send-button").disabled = true;

  // Show progress bar
  document.getElementById("progress-bar").style.display = "block";
  document.getElementById("progress").style.width = "100%"; // Simulate a progress completion

  document.getElementById(
    "chat-box"
  ).innerHTML += `<div class="message sent"> ${userInput}</div>`;

  // Clear the input box
  document.getElementById("user-input").value = "";
  fetch("/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ message: userInput }),
  })
    .then((response) => response.json())
    .then((data) => {
      // Access the output from data.response.output
      let chatbox = document.getElementById("chat-box")
      chatbox.innerHTML += `<div class="message received">${data.response.output}</div>`;
      chatbox.scrollTop = chatbox.scrollHeight;

      // Enable the send button
      document.getElementById("send-button").disabled = false;

      // Hide progress bar
      document.getElementById("progress-bar").style.display = "none";
      document.getElementById("progress").style.width = "0%"; // Reset progress
    })
    .catch((error) => {
      console.error("Error:", error);

      // Enable the send button
      document.getElementById("send-button").disabled = false;

      // Hide progress bar in case of error as well
      document.getElementById("progress-bar").style.display = "none";
      document.getElementById("progress").style.width = "0%"; // Reset progress
    });
}
