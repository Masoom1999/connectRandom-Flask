let currentChatUser = null;
const chatMessages = document.getElementById("chatMessages");
const chatHeader = document.getElementById("chatHeader");
const chatInput = document.getElementById("chatInput");
const sendBtn = document.getElementById("sendBtn");

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".city-user").forEach((el) => {
    el.addEventListener("click", () => {
      currentChatUser = el.dataset.username;
      chatHeader.textContent =
        "Chat with " + el.querySelector("p").textContent.split(": ")[1];
      chatMessages.innerHTML = "";
    });
  });

  sendBtn.addEventListener("click", () => {
    if (!currentChatUser) return alert("Select a user to chat first!");
    if (chatInput.value.trim() === "") return;

    const p = document.createElement("p");
    p.textContent = "You: " + chatInput.value;
    chatMessages.appendChild(p);
    chatInput.value = "";
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // TODO: send message to backend via fetch/AJAX
  });
});
