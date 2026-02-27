(function () {
  "use strict";

  // In-memory conversation history (stateless backend — we send full history each request)
  var conversationHistory = [];
  var isWaiting = false;

  // DOM references (set after DOMContentLoaded)
  var panel, messages, input, sendBtn, toggle;

  function init() {
    panel   = document.getElementById("ai-agent-panel");
    messages = document.getElementById("ai-agent-messages");
    input   = document.getElementById("ai-agent-input");
    sendBtn = document.getElementById("ai-agent-send");
    toggle  = document.getElementById("ai-agent-toggle");

    if (!panel) return; // Safety: widget not present

    toggle.addEventListener("click", openPanel);
    document.getElementById("ai-agent-close").addEventListener("click", closePanel);
    sendBtn.addEventListener("click", sendMessage);

    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });

    // Auto-resize textarea as user types
    input.addEventListener("input", function () {
      this.style.height = "auto";
      this.style.height = Math.min(this.scrollHeight, 100) + "px";
    });

    // Show greeting on first open
    appendMessage(
      "assistant",
      "Hello! I\u2019m your GeoNode AI Assistant \uD83E\uDDED\n\n" +
      "I can help you search for GIS layers and datasets. Try asking:\n" +
      "\u2022 \u201CFind flood risk layers\u201D\n" +
      "\u2022 \u201CSearch for road network data\u201D\n" +
      "\u2022 \u201CShow me satellite imagery\u201D"
    );
  }

  function openPanel() {
    panel.classList.add("open");
    toggle.style.display = "none";
    input.focus();
  }

  function closePanel() {
    panel.classList.remove("open");
    toggle.style.display = "";
  }

  function appendMessage(role, text) {
    var div = document.createElement("div");
    div.className = "ai-msg " + role;
    div.textContent = text;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
    return div;
  }

  function sendMessage() {
    if (isWaiting) return;
    var text = input.value.trim();
    if (!text) return;

    // Clear input and reset height
    input.value = "";
    input.style.height = "auto";

    // Show user message
    appendMessage("user", text);

    // Show thinking indicator
    var thinkingDiv = appendMessage("thinking", "Searching layers\u2026");
    isWaiting = true;
    sendBtn.disabled = true;

    // History for this request = everything BEFORE the current user message
    var historyToSend = conversationHistory.slice();

    // Now record the user message in history
    conversationHistory.push({ role: "user", content: text });

    var chatUrl = window.AI_AGENT_CHAT_URL || "/ai-agent/chat/";

    fetch(chatUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, history: historyToSend }),
    })
      .then(function (resp) {
        return resp.json();
      })
      .then(function (data) {
        thinkingDiv.remove();
        if (data.error) {
          appendMessage("error", "Error: " + (data.error || "Unknown error"));
          // Remove the failed user message from history
          conversationHistory.pop();
        } else {
          var reply = data.reply || "";
          appendMessage("assistant", reply);
          conversationHistory.push({ role: "assistant", content: reply });
        }
      })
      .catch(function () {
        thinkingDiv.remove();
        appendMessage("error", "Network error. Please check your connection and try again.");
        conversationHistory.pop();
      })
      .finally(function () {
        isWaiting = false;
        sendBtn.disabled = false;
        input.focus();
      });
  }

  // Initialize once DOM is ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
