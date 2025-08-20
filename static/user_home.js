// user_home.js
// Frontend chat UI logic: fetch messages, render, send messages, keep scroll and alignment

(function () {
  // Elements
  const chatMessages = document.getElementById("chatMessages");
  const chatHeader = document.getElementById("chatHeader");
  const chatInput = document.getElementById("chatInput");
  const sendBtn = document.getElementById("sendBtn");
  const cityUserEls = document.querySelectorAll(".city-user");
  let currentChatUser = null;

  // --- Helpers ---
  function createMessageElement(msg, currentUser) {
    // msg: { from_user, to_user, message_content, timestamp? }
    const wrapper = document.createElement("div");
    wrapper.classList.add("message");

    const isSent = String(msg.from_user) === String(currentUser);
    wrapper.classList.add(isSent ? "sent" : "received");

    const label = document.createElement("strong");
    label.style.marginRight = "8px";
    label.textContent = isSent ? "You:" : `${msg.from_user}:`;

    const text = document.createElement("span");
    text.textContent = msg.message_content;

    wrapper.appendChild(label);
    wrapper.appendChild(text);
    return wrapper;
  }

  function safeEncodeURIComponent(s) {
    try {
      return encodeURIComponent(s);
    } catch (e) {
      return encodeURIComponent(String(s));
    }
  }

  function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function setActiveUserElement(username) {
    cityUserEls.forEach((el) => {
      if (el.dataset.username === username) el.classList.add("active");
      else el.classList.remove("active");
    });
  }

  // adjust chat messages container height to avoid overflow (improves reliability)
  function adjustChatHeight() {
    const header = document.querySelector("header");
    const footer = document.querySelector("footer");
    const chatWindow = document.querySelector(".chat-window");
    const chatInputRow = document.querySelector(".chat-input");

    if (!chatWindow || !chatMessages) return;

    const headerH = header ? header.getBoundingClientRect().height : 0;
    const footerH = footer ? footer.getBoundingClientRect().height : 0;
    const windowH = window.innerHeight;

    // top of chatWindow
    const chatTop = chatWindow.getBoundingClientRect().top;
    // compute available height for messages area: up to footer minus header and input row
    const inputH = chatInputRow ? chatInputRow.getBoundingClientRect().height : 60;
    const available = Math.max(200, windowH - chatTop - footerH - inputH - 36); // safe minimum 200px

    chatMessages.style.height = available + "px";
    chatMessages.style.maxHeight = available + "px";
  }

  // --- Fetch & render ---
  async function fetchMessages(chatWith) {
    if (!chatWith) return;
    chatMessages.innerHTML = '<p style="color:#666">Loading messages...</p>';
    try {
      const res = await fetch(`/get_messages/${safeEncodeURIComponent(chatWith)}`, {
        method: "GET",
        headers: { "Accept": "application/json" },
      });

      if (!res.ok) {
        // show friendly message
        chatMessages.innerHTML = `<p style="color:#c00">No messages found or server returned ${res.status}</p>`;
        return;
      }

      const payload = await res.json();
      // payload expected: { status: 'success', messages: [ ... ] } or direct messages array
      const messages = payload.messages || payload || [];

      renderMessages(messages);
    } catch (err) {
      console.error("fetchMessages error:", err);
      chatMessages.innerHTML = '<p style="color:#c00">Error loading messages</p>';
    }
  }

  function renderMessages(messages) {
    chatMessages.innerHTML = "";
    if (!Array.isArray(messages) || messages.length === 0) {
      chatMessages.innerHTML = '<p style="color:#666">No messages yet. Start the conversation!</p>';
      return;
    }

    // assume messages already ordered ascending (oldest first) from backend
    messages.forEach((m) => {
      const el = createMessageElement(m, CURRENT_USERNAME);
      chatMessages.appendChild(el);
    });

    scrollToBottom();
  }

  // append a single local message optimistically
  function appendLocalMessage(msg) {
    const el = createMessageElement(msg, CURRENT_USERNAME);
    chatMessages.appendChild(el);
    scrollToBottom();
  }

  // --- Sending messages ---
  async function sendMessage() {
    if (!currentChatUser) {
      alert("Select a user to chat with first.");
      return;
    }
    const text = chatInput.value.trim();
    if (!text) return;

    // optimistic UI update
    const tempMsg = {
      from_user: CURRENT_USERNAME,
      to_user: currentChatUser,
      message_content: text,
      timestamp: new Date().toISOString(),
    };
    appendLocalMessage(tempMsg);
    chatInput.value = "";

    try {
      const res = await fetch("/send_message", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({
          from_user: CURRENT_USERNAME,
          to_user: currentChatUser,
          message_content: text,
        }),
      });

      if (!res.ok) {
        const txt = await res.text().catch(() => "");
        console.error("send_message failed:", res.status, txt);
        alert("Failed to send message (server error).");
        // Optionally: re-fetch to restore actual server state
        fetchMessages(currentChatUser);
        return;
      }

      const payload = await res.json().catch(() => ({}));
      if (payload && payload.status === "error") {
        alert(payload.message || "Failed to send message");
        fetchMessages(currentChatUser);
        return;
      }

      // success — refresh messages from server (to get canonical ordering/ids)
      fetchMessages(currentChatUser);
    } catch (err) {
      console.error("sendMessage error:", err);
      alert("Failed to send message (network error).");
      fetchMessages(currentChatUser);
    }
  }

  // --- Event wiring ---
  document.addEventListener("DOMContentLoaded", () => {
    // wire up city user click
    cityUserEls.forEach((el) => {
      el.addEventListener("click", () => {
        const username = el.dataset.username;
        if (!username) return;
        currentChatUser = username;

        // display readable name if available
        const nameEl = el.querySelector("p");
        let displayName = username;
        if (nameEl) {
          const parts = nameEl.textContent.split(":");
          if (parts.length > 1) displayName = parts.slice(1).join(":").trim();
        }

        chatHeader.textContent = `Chat with ${displayName}`;
        setActiveUserElement(username);

        // adjust height and fetch messages for this chat
        adjustChatHeight();
        fetchMessages(username);
      });
    });

    // send button
    sendBtn.addEventListener("click", (e) => {
      e.preventDefault();
      sendMessage();
    });

    // allow Enter to send (Shift+Enter for newline)
    chatInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });

    // adjust sizes on load and resize
    window.addEventListener("resize", adjustChatHeight);
    adjustChatHeight();
  });
})();
