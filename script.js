"use strict";

/* ============================================================
   RURAL HEALTH AI - FRONTEND
   English + Tamil + Hindi
   Text + Voice Recognition + Manual Voice Output
============================================================ */

const API_URL = "/chat";
const HEALTH_URL = "/health";

/* ============================================================
   DOM
============================================================ */

const welcomeOverlay = document.getElementById("welcome-overlay");
const welcomeStartBtn = document.getElementById("welcome-start-btn");

const languageSelect = document.getElementById("language-select");
const chatContainer = document.getElementById("chat-container");

const userInput = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");
const voiceBtn = document.getElementById("voice-btn");

const clearBtn = document.getElementById("clear-btn");
const charCounter = document.getElementById("char-counter");

const statusDot = document.getElementById("status-dot");

const topicButtons = document.querySelectorAll(".topic-btn");
const exampleButtons = document.querySelectorAll(".example-q");

/* ============================================================
   STATE
============================================================ */

let isSending = false;
let isListening = false;
let recognition = null;

let selectedLanguage = "en";

/* Voice state */
let currentUtterance = null;
let currentSpeakButton = null;

/* ============================================================
   LANGUAGE CONFIG
============================================================ */

const languageConfig = {

    en: {
        speech: "en-IN",
        placeholder: "Type your health question…",
        listening: "Listening…",
        start: "Speak your question",
        stop: "Stop listening",
        listen: "🔊 Listen",
        stopSpeaking: "⏹ Stop"
    },

    ta: {
        speech: "ta-IN",
        placeholder: "உங்கள் உடல்நல கேள்வியை உள்ளிடுங்கள்…",
        listening: "கேட்கிறது…",
        start: "உங்கள் கேள்வியை பேசுங்கள்",
        stop: "கேட்பதை நிறுத்து",
        listen: "🔊 கேளுங்கள்",
        stopSpeaking: "⏹ நிறுத்து"
    },

    hi: {
        speech: "hi-IN",
        placeholder: "अपना स्वास्थ्य प्रश्न लिखें…",
        listening: "सुन रहा है…",
        start: "अपना प्रश्न बोलें",
        stop: "सुनना बंद करें",
        listen: "🔊 सुनें",
        stopSpeaking: "⏹ रोकें"
    }
};

/* ============================================================
   INITIALIZE
============================================================ */

document.addEventListener("DOMContentLoaded", () => {

    setupWelcome();
    setupLanguage();
    setupInput();
    setupSendButton();
    setupVoiceRecognition();
    setupClearButton();
    setupTopicButtons();
    setupExampleButtons();

    updateLanguageUI();
    updateCharCounter();
    checkBackendStatus();

    /* Load browser voices */
    if ("speechSynthesis" in window) {
        window.speechSynthesis.getVoices();

        window.speechSynthesis.onvoiceschanged = () => {
            window.speechSynthesis.getVoices();
        };
    }

});

/* ============================================================
   WELCOME
============================================================ */

function setupWelcome() {

    if (!welcomeOverlay || !welcomeStartBtn) {
        return;
    }

    welcomeStartBtn.addEventListener("click", () => {

        welcomeOverlay.classList.add("hidden");

        setTimeout(() => {

            if (userInput) {
                userInput.focus();
            }

        }, 200);

    });

}

/* ============================================================
   LANGUAGE
============================================================ */

function setupLanguage() {

    if (!languageSelect) {
        return;
    }

    selectedLanguage =
        languageSelect.value || "en";

    languageSelect.addEventListener("change", () => {

        /* Stop any current speech */
        stopSpeaking();

        selectedLanguage =
            languageSelect.value || "en";

        updateLanguageUI();

        if (isListening) {
            stopVoiceRecognition();
        }

    });

}

function updateLanguageUI() {

    const config =
        languageConfig[selectedLanguage] ||
        languageConfig.en;

    if (userInput) {
        userInput.placeholder =
            config.placeholder;
    }

    if (voiceBtn) {

        voiceBtn.title =
            config.start;

        voiceBtn.setAttribute(
            "aria-label",
            config.start
        );

    }

}

/* ============================================================
   INPUT
============================================================ */

function setupInput() {

    if (!userInput) {
        return;
    }

    userInput.addEventListener("input", () => {

        updateCharCounter();
        updateSendButton();
        autoResizeTextarea();

    });

    userInput.addEventListener("keydown", event => {

        if (
            event.key === "Enter" &&
            !event.shiftKey
        ) {

            event.preventDefault();

            if (
                !isSending &&
                userInput.value.trim()
            ) {
                sendMessage();
            }

        }

    });

}

function autoResizeTextarea() {

    if (!userInput) {
        return;
    }

    userInput.style.height = "auto";

    userInput.style.height =
        Math.min(
            userInput.scrollHeight,
            120
        ) + "px";

}

/* ============================================================
   CHARACTER COUNTER
============================================================ */

function updateCharCounter() {

    if (!userInput || !charCounter) {
        return;
    }

    const length =
        userInput.value.length;

    charCounter.textContent =
        `${length} / 500`;

    charCounter.classList.toggle(
        "warn",
        length >= 450
    );

}

/* ============================================================
   SEND BUTTON
============================================================ */

function setupSendButton() {

    if (!sendBtn) {
        return;
    }

    sendBtn.addEventListener(
        "click",
        () => {

            if (!isSending) {
                sendMessage();
            }

        }
    );

    updateSendButton();

}

function updateSendButton() {

    if (!sendBtn || !userInput) {
        return;
    }

    const hasText =
        userInput.value.trim().length > 0;

    sendBtn.disabled =
        !hasText || isSending;

}

/* ============================================================
   SEND MESSAGE
============================================================ */

async function sendMessage(messageOverride = null) {

    if (isSending) {
        return;
    }

    let message =
        messageOverride !== null
            ? String(messageOverride).trim()
            : userInput.value.trim();

    if (!message) {
        return;
    }

    if (message.length > 500) {
        message =
            message.substring(0, 500);
    }

    /* Stop previous speech before new request */
    stopSpeaking();

    addMessage(
        message,
        "user"
    );

    if (userInput) {

        userInput.value = "";
        userInput.style.height = "auto";

    }

    updateCharCounter();

    isSending = true;
    updateSendButton();

    setStatus("busy");

    const typingId =
        showTypingIndicator();

    try {

        const response =
            await fetch(
                API_URL,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json",

                        "Accept":
                            "application/json"
                    },

                    body: JSON.stringify({
                        message: message,
                        language: selectedLanguage
                    })
                }
            );

        if (!response.ok) {

            let errorMessage =
                `Server error (${response.status})`;

            try {

                const errorData =
                    await response.json();

                if (
                    errorData &&
                    errorData.reply
                ) {

                    errorMessage =
                        errorData.reply;

                }

            } catch (_) {}

            throw new Error(
                errorMessage
            );

        }

        const data =
            await response.json();

        console.log(
            "Rural Health AI response:",
            data
        );

        removeTypingIndicator(
            typingId
        );

        const reply =
            typeof data.reply === "string"
                ? data.reply.trim()
                : "";

        if (!reply) {

            throw new Error(
                "The AI returned an empty response."
            );

        }

        /*
           IMPORTANT:
           DO NOT automatically speak here.
           User must click Listen button.
        */

        addMessage(
            reply,
            "bot",
            Boolean(data.emergency)
        );

        setStatus("online");

    } catch (error) {

        console.error(
            "Chat request failed:",
            error
        );

        removeTypingIndicator(
            typingId
        );

        addErrorMessage(
            getLocalizedError()
        );

        setStatus("error");

    } finally {

        isSending = false;
        updateSendButton();

    }

}

/* ============================================================
   LOCALIZED ERROR
============================================================ */

function getLocalizedError() {

    if (selectedLanguage === "ta") {

        return (
            "⚠️ மன்னிக்கவும். தற்போது AI பதிலை உருவாக்க "
            + "முடியவில்லை. Ollama இயங்குகிறதா என்பதை "
            + "சரிபார்த்து மீண்டும் முயற்சிக்கவும்."
        );

    }

    if (selectedLanguage === "hi") {

        return (
            "⚠️ क्षमा करें। अभी AI उत्तर नहीं दे सका। "
            + "कृपया Ollama की स्थिति जांचें और फिर प्रयास करें।"
        );

    }

    return (
        "⚠️ Sorry, I could not process your question. "
        + "Please check that Ollama is running and try again."
    );

}

/* ============================================================
   MESSAGE
============================================================ */

function addMessage(
    text,
    sender = "bot",
    emergency = false
) {

    if (!chatContainer) {
        return;
    }

    const row =
        document.createElement("div");

    row.className =
        sender === "user"
            ? "msg-row user"
            : "msg-row";

    const avatar =
        document.createElement("div");

    avatar.className =
        sender === "user"
            ? "avatar user"
            : "avatar bot";

    avatar.textContent =
        sender === "user"
            ? "👤"
            : emergency
                ? "⚠️"
                : "🩺";

    const wrap =
        document.createElement("div");

    wrap.className =
        "bubble-wrap";

    const bubble =
        document.createElement("div");

    bubble.className =
        sender === "user"
            ? "bubble user"
            : "bubble bot";

    if (
        sender === "bot" &&
        emergency
    ) {

        bubble.classList.add(
            "emergency"
        );

    }

    /*
       textContent is intentionally used.
       This prevents HTML injection.
    */

    bubble.textContent = text;

    const meta =
        document.createElement("div");

    meta.className =
        "msg-meta";

    const time =
        document.createElement("span");

    time.className =
        "msg-time";

    time.textContent =
        getCurrentTime();

    meta.appendChild(time);

    if (sender === "bot") {

        /* COPY BUTTON */

        const copyBtn =
            document.createElement("button");

        copyBtn.type = "button";
        copyBtn.className = "copy-btn";
        copyBtn.textContent = "📋 Copy";

        copyBtn.addEventListener(
            "click",
            () => copyText(
                text,
                copyBtn
            )
        );

        meta.appendChild(
            copyBtn
        );

        /* LISTEN BUTTON */

        const listenBtn =
            document.createElement("button");

        listenBtn.type = "button";
        listenBtn.className = "listen-btn";

        const config =
            languageConfig[selectedLanguage] ||
            languageConfig.en;

        listenBtn.textContent =
            config.listen;

        listenBtn.setAttribute(
            "aria-label",
            "Listen to response"
        );

        listenBtn.addEventListener(
            "click",
            () => {

                if (
                    currentSpeakButton === listenBtn &&
                    window.speechSynthesis &&
                    window.speechSynthesis.speaking
                ) {

                    stopSpeaking();
                    return;

                }

                speakResponse(
                    text,
                    listenBtn
                );

            }
        );

        meta.appendChild(
            listenBtn
        );

    }

    wrap.appendChild(bubble);
    wrap.appendChild(meta);

    row.appendChild(avatar);
    row.appendChild(wrap);

    chatContainer.appendChild(row);

    scrollChatToBottom();

}

/* ============================================================
   ERROR MESSAGE
============================================================ */

function addErrorMessage(text) {

    if (!chatContainer) {
        return;
    }

    const row =
        document.createElement("div");

    row.className =
        "msg-row";

    const avatar =
        document.createElement("div");

    avatar.className =
        "avatar bot";

    avatar.textContent =
        "⚠️";

    const wrap =
        document.createElement("div");

    wrap.className =
        "bubble-wrap";

    const bubble =
        document.createElement("div");

    bubble.className =
        "error-bubble";

    bubble.textContent =
        text;

    wrap.appendChild(
        bubble
    );

    row.appendChild(
        avatar
    );

    row.appendChild(
        wrap
    );

    chatContainer.appendChild(
        row
    );

    scrollChatToBottom();

}

/* ============================================================
   TYPING
============================================================ */

function showTypingIndicator() {

    if (!chatContainer) {
        return null;
    }

    const id =
        "typing-" + Date.now();

    const row =
        document.createElement("div");

    row.id = id;
    row.className =
        "typing-row";

    const avatar =
        document.createElement("div");

    avatar.className =
        "avatar bot";

    avatar.textContent =
        "🩺";

    const indicator =
        document.createElement("div");

    indicator.className =
        "typing-indicator";

    for (let i = 0; i < 3; i++) {

        const dot =
            document.createElement("span");

        dot.className =
            "typing-dot";

        indicator.appendChild(
            dot
        );

    }

    row.appendChild(
        avatar
    );

    row.appendChild(
        indicator
    );

    chatContainer.appendChild(
        row
    );

    scrollChatToBottom();

    return id;

}

function removeTypingIndicator(id) {

    if (!id) {
        return;
    }

    const element =
        document.getElementById(id);

    if (element) {
        element.remove();
    }

}

/* ============================================================
   SCROLL
============================================================ */

function scrollChatToBottom() {

    if (!chatContainer) {
        return;
    }

    requestAnimationFrame(() => {

        chatContainer.scrollTo({
            top: chatContainer.scrollHeight,
            behavior: "smooth"
        });

    });

}

/* ============================================================
   TIME
============================================================ */

function getCurrentTime() {

    return new Intl.DateTimeFormat(
        "en-IN",
        {
            hour: "2-digit",
            minute: "2-digit"
        }
    ).format(
        new Date()
    );

}

/* ============================================================
   COPY
============================================================ */

async function copyText(
    text,
    button
) {

    try {

        await navigator.clipboard.writeText(
            text
        );

        button.textContent =
            "✓ Copied";

        setTimeout(() => {

            button.textContent =
                "📋 Copy";

        }, 1500);

    } catch (error) {

        console.error(
            "Copy failed:",
            error
        );

    }

}

/* ============================================================
   CLEAR
============================================================ */

function setupClearButton() {

    if (!clearBtn) {
        return;
    }

    clearBtn.addEventListener(
        "click",
        () => {

            /* Stop voice */
            stopSpeaking();

            if (chatContainer) {
                chatContainer.innerHTML = "";
            }

            if (userInput) {

                userInput.value = "";
                userInput.focus();

            }

            updateCharCounter();
            updateSendButton();

            setStatus("online");

        }
    );

}

/* ============================================================
   QUICK TOPICS
============================================================ */

function setupTopicButtons() {

    topicButtons.forEach(button => {

        button.addEventListener(
            "click",
            () => {

                const question =
                    getLocalizedQuestion(
                        button
                    );

                if (
                    question &&
                    !isSending
                ) {

                    sendMessage(
                        question
                    );

                }

            }
        );

    });

}

/* ============================================================
   EXAMPLES
============================================================ */

function setupExampleButtons() {

    exampleButtons.forEach(button => {

        button.addEventListener(
            "click",
            () => {

                const question =
                    getLocalizedQuestion(
                        button
                    );

                if (
                    question &&
                    !isSending
                ) {

                    sendMessage(
                        question
                    );

                }

            }
        );

    });

}

/* ============================================================
   LOCALIZED QUESTION
============================================================ */

function getLocalizedQuestion(element) {

    if (!element) {
        return "";
    }

    const translated =
        element.getAttribute(
            `data-${selectedLanguage}`
        );

    if (translated) {
        return translated.trim();
    }

    const english =
        element.getAttribute(
            "data-en"
        );

    if (english) {
        return english.trim();
    }

    return element.textContent.trim();

}

/* ============================================================
   SPEECH RECOGNITION
============================================================ */

function setupVoiceRecognition() {

    if (!voiceBtn) {
        return;
    }

    const SpeechRecognition =
        window.SpeechRecognition ||
        window.webkitSpeechRecognition;

    if (!SpeechRecognition) {

        voiceBtn.disabled = true;

        voiceBtn.title =
            "Voice recognition is not supported in this browser.";

        return;
    }

    recognition =
        new SpeechRecognition();

    recognition.continuous = false;
    recognition.interimResults = true;

    recognition.onstart = () => {

        isListening = true;

        voiceBtn.classList.add(
            "listening"
        );

        const config =
            languageConfig[
                selectedLanguage
            ] || languageConfig.en;

        voiceBtn.title =
            config.stop;

    };

    recognition.onresult = event => {

        let transcript = "";

        for (
            let i = event.resultIndex;
            i < event.results.length;
            i++
        ) {

            transcript +=
                event.results[i][0].transcript;

        }

        if (userInput) {

            userInput.value =
                transcript.trim();

            updateCharCounter();
            updateSendButton();
            autoResizeTextarea();

        }

    };

    recognition.onerror = event => {

        console.error(
            "Speech recognition error:",
            event.error
        );

        isListening = false;

        resetVoiceButton();

    };

    recognition.onend = () => {

        isListening = false;

        resetVoiceButton();

    };

    voiceBtn.addEventListener(
        "click",
        () => {

            if (isListening) {

                stopVoiceRecognition();

            } else {

                startVoiceRecognition();

            }

        }
    );

}

/* ============================================================
   START VOICE RECOGNITION
============================================================ */

function startVoiceRecognition() {

    if (!recognition) {
        return;
    }

    try {

        recognition.lang =
            languageConfig[
                selectedLanguage
            ].speech;

        recognition.start();

    } catch (error) {

        console.error(
            "Voice start error:",
            error
        );

    }

}

/* ============================================================
   STOP VOICE RECOGNITION
============================================================ */

function stopVoiceRecognition() {

    if (!recognition) {
        return;
    }

    try {

        recognition.stop();

    } catch (_) {}

}

/* ============================================================
   RESET VOICE BUTTON
============================================================ */

function resetVoiceButton() {

    if (!voiceBtn) {
        return;
    }

    voiceBtn.classList.remove(
        "listening"
    );

    const config =
        languageConfig[
            selectedLanguage
        ] || languageConfig.en;

    voiceBtn.title =
        config.start;

}

/* ============================================================
   TEXT TO SPEECH
   MANUAL ONLY
============================================================ */

function speakResponse(
    text,
    button = null
) {

    if (
        !("speechSynthesis" in window) ||
        !text
    ) {
        return;
    }

    /* Stop any previous speech */
    stopSpeaking();

    try {

        const utterance =
            new SpeechSynthesisUtterance(
                text
            );

        currentUtterance =
            utterance;

        currentSpeakButton =
            button;

        const config =
            languageConfig[
                selectedLanguage
            ] || languageConfig.en;

        utterance.lang =
            config.speech;

        /*
           Natural speaking speed.
           Slightly slower for Indian languages.
        */

        utterance.rate =
            selectedLanguage === "en"
                ? 0.92
                : 0.88;

        utterance.pitch = 1.0;
        utterance.volume = 1.0;

        /*
           Get all browser/system voices.
        */

        let voices =
            window.speechSynthesis
                .getVoices();

        /*
           Sometimes Chrome loads voices
           asynchronously.
        */

        if (!voices.length) {

            window.speechSynthesis.onvoiceschanged =
                () => {

                    voices =
                        window.speechSynthesis
                            .getVoices();

                };

        }

        const targetLanguage =
            selectedLanguage === "ta"
                ? "ta"
                : selectedLanguage === "hi"
                    ? "hi"
                    : "en";

        /*
           Voice priority:
           1. Exact language
           2. Indian language
           3. Language prefix
        */

        let voice =
            voices.find(
                v =>
                    v.lang &&
                    v.lang.toLowerCase() ===
                    config.speech.toLowerCase()
            );

        if (!voice) {

            voice =
                voices.find(
                    v =>
                        v.lang &&
                        v.lang
                            .toLowerCase()
                            .startsWith(
                                targetLanguage
                            )
                );

        }

        /*
           For English prefer Indian English.
        */

        if (
            !voice &&
            selectedLanguage === "en"
        ) {

            voice =
                voices.find(
                    v =>
                        v.lang &&
                        v.lang
                            .toLowerCase()
                            .includes("en-in")
                );

        }

        if (voice) {
            utterance.voice = voice;
        }

        const originalText =
            button
                ? button.textContent
                : "";

        if (button) {

            button.textContent =
                config.stopSpeaking;

            button.classList.add(
                "speaking"
            );

        }

        utterance.onend = () => {

            if (
                button &&
                currentSpeakButton === button
            ) {

                button.textContent =
                    config.listen;

                button.classList.remove(
                    "speaking"
                );

            }

            currentUtterance = null;
            currentSpeakButton = null;

        };

        utterance.onerror = event => {

            console.error(
                "Speech output error:",
                event.error
            );

            if (button) {

                button.textContent =
                    config.listen;

                button.classList.remove(
                    "speaking"
                );

            }

            currentUtterance = null;
            currentSpeakButton = null;

        };

        window.speechSynthesis.speak(
            utterance
        );

    } catch (error) {

        console.error(
            "Speech output error:",
            error
        );

        currentUtterance = null;
        currentSpeakButton = null;

    }

}

/* ============================================================
   STOP SPEAKING
============================================================ */

function stopSpeaking() {

    if (
        "speechSynthesis" in window
    ) {

        window.speechSynthesis.cancel();

    }

    if (currentSpeakButton) {

        const config =
            languageConfig[
                selectedLanguage
            ] || languageConfig.en;

        currentSpeakButton.textContent =
            config.listen;

        currentSpeakButton.classList.remove(
            "speaking"
        );

    }

    currentUtterance = null;
    currentSpeakButton = null;

}

/* ============================================================
   BACKEND STATUS
============================================================ */

async function checkBackendStatus() {

    if (!statusDot) {
        return;
    }

    try {

        const response =
            await fetch(
                HEALTH_URL,
                {
                    method: "GET",
                    cache: "no-store"
                }
            );

        if (!response.ok) {

            throw new Error(
                "Backend unavailable"
            );

        }

        const data =
            await response.json();

        if (
            data.status === "ok" &&
            data.model_available
        ) {

            setStatus("online");

        } else {

            setStatus("error");

        }

    } catch (error) {

        console.error(
            "Backend status:",
            error
        );

        setStatus("error");

    }

}

/* ============================================================
   STATUS
============================================================ */

function setStatus(status) {

    if (!statusDot) {
        return;
    }

    statusDot.classList.remove(
        "busy",
        "error"
    );

    if (status === "busy") {

        statusDot.classList.add(
            "busy"
        );

    }

    if (status === "error") {

        statusDot.classList.add(
            "error"
        );

    }

}

/* ============================================================
   CLEANUP
============================================================ */

window.addEventListener(
    "beforeunload",
    () => {

        stopSpeaking();

        if (recognition) {

            try {
                recognition.stop();
            } catch (_) {}

        }

    }
);

/* ============================================================
   DEBUG API
============================================================ */

window.RuralHealthAI = {

    sendMessage,

    checkBackendStatus,

    startVoiceRecognition,

    stopVoiceRecognition,

    speakResponse,

    stopSpeaking,

    getLanguage: () =>
        selectedLanguage

};

console.log(
    "✓ Rural Health AI frontend initialized."
);