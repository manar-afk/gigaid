/**
 * Gig-Aid: Pan-India Multilingual Grievance Assistant
 * Worker-controlled workflow:
 * 1. Describe dispute (via text or optional speech)
 * 2. Clarify missing facts
 * 3. Review, edit, copy, download grievance draft
 * 4. Access verified official Central/State sources & next steps
 */

(() => {
  "use strict";

  // State Management
  const state = {
    currentDraftResponse: null,
    isRecording: false,
    isPlayingAudio: false,
    speechRecognition: null,
    synth: window.speechSynthesis || null,
    currentUtterance: null,
  };

  // DOM Elements
  const disputeForm = document.getElementById("dispute-form");
  const platformInput = document.getElementById("platform-input");
  const categorySelect = document.getElementById("category-select");
  const stateInput = document.getElementById("state-input");
  const preferredLangSelect = document.getElementById("preferred-lang");
  const narrativeTextarea = document.getElementById("dispute-narrative");
  const charCountDisplay = document.getElementById("char-count");
  const formErrorAlert = document.getElementById("form-error-alert");

  const generateDraftBtn = document.getElementById("generate-draft-btn");
  const btnSpinner = document.getElementById("btn-spinner");
  const btnText = document.getElementById("btn-text");

  // Speech elements
  const voiceRecordBtn = document.getElementById("voice-record-btn");
  const voiceRecordText = document.getElementById("voice-record-text");
  const voiceStatusBar = document.getElementById("voice-status-bar");
  const voiceStatusText = document.getElementById("voice-status-text");

  // Audio readout elements
  const audioReadoutBtn = document.getElementById("audio-readout-btn");
  const audioReadoutText = document.getElementById("audio-readout-text");

  // Clarification section
  const clarificationSection = document.getElementById("clarification-section");
  const missingQuestionsList = document.getElementById("missing-questions-list");
  const updateDraftWithFactsBtn = document.getElementById("update-draft-with-facts-btn");

  // Draft output section
  const draftOutputSection = document.getElementById("draft-output-section");
  const workerSummaryText = document.getElementById("worker-summary-text");
  const draftSubjectInput = document.getElementById("draft-subject-input");
  const draftBodyTextarea = document.getElementById("draft-body-textarea");
  const copyDraftBtn = document.getElementById("copy-draft-btn");
  const downloadDraftBtn = document.getElementById("download-draft-btn");
  const copyStatusMsg = document.getElementById("copy-status-msg");

  // Breakdown lists
  const workerFactsList = document.getElementById("worker-facts-list");
  const verifiedGuidanceList = document.getElementById("verified-guidance-list");
  const unverifiedInfoList = document.getElementById("unverified-info-list");
  const nextStepsList = document.getElementById("next-steps-list");

  // Stepper elements
  const stepNav1 = document.getElementById("step-nav-1");
  const stepNav2 = document.getElementById("step-nav-2");
  const stepNav3 = document.getElementById("step-nav-3");
  const stepNav4 = document.getElementById("step-nav-4");

  // Language mapping for Web Speech Recognition & Synthesis
  const LANG_BCP47_MAP = {
    English: "en-IN",
    Hindi: "hi-IN",
    Hinglish: "hi-IN",
    Tamil: "ta-IN",
    Telugu: "te-IN",
    Kannada: "kn-IN",
    Bengali: "bn-IN",
  };

  // Initialize Speech Recognition if supported
  function setupSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      if (voiceRecordBtn) {
        voiceRecordBtn.title = "Voice input is not supported by your current browser. You can type freely.";
      }
      return null;
    }

    const recognizer = new SpeechRecognition();
    recognizer.continuous = false;
    recognizer.interimResults = true;

    recognizer.onstart = () => {
      state.isRecording = true;
      voiceRecordBtn.setAttribute("aria-pressed", "true");
      voiceRecordBtn.classList.add("btn-recording");
      voiceRecordText.textContent = "Stop Recording";
      voiceStatusBar.style.display = "flex";
      voiceStatusText.textContent = "Listening... Speak clearly now.";
    };

    recognizer.onresult = (event) => {
      let interimTranscript = "";
      let finalTranscript = "";

      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          finalTranscript += event.results[i][0].transcript;
        } else {
          interimTranscript += event.results[i][0].transcript;
        }
      }

      if (finalTranscript) {
        const separator = narrativeTextarea.value.trim() ? " " : "";
        narrativeTextarea.value = narrativeTextarea.value.trim() + separator + finalTranscript;
        updateCharCount();
      }
    };

    recognizer.onerror = (event) => {
      console.warn("Speech recognition error:", event.error);
      stopVoiceRecording();
      voiceStatusBar.style.display = "flex";
      voiceStatusText.textContent = `Speech input note: ${event.error}. You can continue by typing.`;
    };

    recognizer.onend = () => {
      stopVoiceRecording();
    };

    return recognizer;
  }

  function startVoiceRecording() {
    if (!state.speechRecognition) {
      state.speechRecognition = setupSpeechRecognition();
    }
    if (!state.speechRecognition) {
      alert("Speech recognition is not supported in this browser. Please type your dispute.");
      return;
    }

    const currentLang = preferredLangSelect.value;
    state.speechRecognition.lang = LANG_BCP47_MAP[currentLang] || "en-IN";

    try {
      state.speechRecognition.start();
    } catch (err) {
      console.warn("Could not start recognizer:", err);
    }
  }

  function stopVoiceRecording() {
    state.isRecording = false;
    voiceRecordBtn.setAttribute("aria-pressed", "false");
    voiceRecordBtn.classList.remove("btn-recording");
    voiceRecordText.textContent = "Voice Input (Optional)";
    if (state.speechRecognition) {
      try {
        state.speechRecognition.stop();
      } catch (_) {}
    }
    setTimeout(() => {
      if (!state.isRecording) {
        voiceStatusBar.style.display = "none";
      }
    }, 2500);
  }

  // Audio Readout (TTS)
  function toggleAudioReadout(textToRead) {
    if (!state.synth) {
      alert("Audio readout is not supported by your browser.");
      return;
    }

    if (state.isPlayingAudio) {
      state.synth.cancel();
      state.isPlayingAudio = false;
      audioReadoutBtn.setAttribute("aria-pressed", "false");
      audioReadoutText.textContent = "Listen Summary";
      return;
    }

    if (!textToRead || !textToRead.trim()) return;

    state.synth.cancel(); // Clear any ongoing speech
    const utterance = new SpeechSynthesisUtterance(textToRead);
    const currentLang = preferredLangSelect.value;
    utterance.lang = LANG_BCP47_MAP[currentLang] || "en-IN";
    utterance.rate = 0.95;

    utterance.onstart = () => {
      state.isPlayingAudio = true;
      audioReadoutBtn.setAttribute("aria-pressed", "true");
      audioReadoutText.textContent = "Stop Audio";
    };

    utterance.onend = () => {
      state.isPlayingAudio = false;
      audioReadoutBtn.setAttribute("aria-pressed", "false");
      audioReadoutText.textContent = "Listen Summary";
    };

    utterance.onerror = () => {
      state.isPlayingAudio = false;
      audioReadoutBtn.setAttribute("aria-pressed", "false");
      audioReadoutText.textContent = "Listen Summary";
    };

    state.currentUtterance = utterance;
    state.synth.speak(utterance);
  }

  // Live character count
  function updateCharCount() {
    const len = narrativeTextarea.value.length;
    charCountDisplay.textContent = `${len} / 4000`;
  }

  // Clear errors
  function clearError() {
    formErrorAlert.style.display = "none";
    formErrorAlert.textContent = "";
  }

  function showError(msg) {
    formErrorAlert.style.display = "block";
    formErrorAlert.textContent = msg;
    formErrorAlert.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  // Update Stepper Navigation
  function setStep(stepNumber) {
    [stepNav1, stepNav2, stepNav3, stepNav4].forEach((el, index) => {
      if (index + 1 === stepNumber) {
        el.classList.add("step-active");
      } else {
        el.classList.remove("step-active");
      }
    });
  }

  // Render Verification Breakdown Lists
  function renderBreakdown(factStatus) {
    // 1. Worker Facts
    workerFactsList.innerHTML = "";
    if (factStatus.worker_provided_facts && factStatus.worker_provided_facts.length > 0) {
      factStatus.worker_provided_facts.forEach((fact) => {
        const li = document.createElement("li");
        li.textContent = fact;
        workerFactsList.appendChild(li);
      });
    } else {
      const li = document.createElement("li");
      li.textContent = "No specific facts extracted.";
      workerFactsList.appendChild(li);
    }

    // 2. Verified Official Guidance
    verifiedGuidanceList.innerHTML = "";
    if (factStatus.verified_guidance && factStatus.verified_guidance.length > 0) {
      factStatus.verified_guidance.forEach((g) => {
        const li = document.createElement("li");
        const titleSpan = document.createElement("strong");
        titleSpan.textContent = `${g.title} (${g.jurisdiction})`;
        li.appendChild(titleSpan);

        const summaryP = document.createElement("p");
        summaryP.style.marginTop = "0.25rem";
        summaryP.textContent = g.summary_simple_language;
        li.appendChild(summaryP);

        if (g.source_url) {
          const link = document.createElement("a");
          link.href = g.source_url;
          link.target = "_blank";
          link.rel = "noopener noreferrer";
          link.textContent = `Open Official Source (${g.source_name})`;
          li.appendChild(link);
        }
        verifiedGuidanceList.appendChild(li);
      });
    } else {
      const li = document.createElement("li");
      li.textContent = "No verified guidance available.";
      verifiedGuidanceList.appendChild(li);
    }

    // 3. Unverified Information
    unverifiedInfoList.innerHTML = "";
    if (factStatus.unverified_information && factStatus.unverified_information.length > 0) {
      factStatus.unverified_information.forEach((item) => {
        const li = document.createElement("li");
        li.textContent = item;
        unverifiedInfoList.appendChild(li);
      });
    } else {
      const li = document.createElement("li");
      li.textContent = "All applicable rules confirmed against official central sources.";
      unverifiedInfoList.appendChild(li);
    }
  }

  // Render Worker Next Steps
  function renderNextSteps(steps) {
    nextStepsList.innerHTML = "";
    if (!steps || steps.length === 0) return;

    steps.forEach((st) => {
      const card = document.createElement("div");
      card.className = "step-card";

      const numSpan = document.createElement("span");
      numSpan.className = "step-card-num";
      numSpan.textContent = st.step_number;
      card.appendChild(numSpan);

      const title = document.createElement("h4");
      title.className = "step-card-title";
      title.textContent = st.title;
      card.appendChild(title);

      const desc = document.createElement("p");
      desc.className = "step-card-desc";
      desc.textContent = st.description;
      card.appendChild(desc);

      if (st.official_portal_link) {
        const link = document.createElement("a");
        link.className = "step-card-link";
        link.href = st.official_portal_link;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = "Open Official Portal \u2197";
        card.appendChild(link);
      }

      nextStepsList.appendChild(card);
    });
  }

  // Render Missing Questions
  function renderMissingQuestions(questions) {
    missingQuestionsList.innerHTML = "";
    if (!questions || questions.length === 0) {
      clarificationSection.style.display = "none";
      return;
    }

    questions.forEach((q) => {
      const wrap = document.createElement("div");
      wrap.className = "question-item";

      const qTitle = document.createElement("p");
      qTitle.className = "question-text";
      qTitle.textContent = q.question_text;
      wrap.appendChild(qTitle);

      const qWhy = document.createElement("p");
      qWhy.className = "question-why";
      qWhy.textContent = `Why this helps: ${q.why_needed}`;
      wrap.appendChild(qWhy);

      const input = document.createElement("input");
      input.type = "text";
      input.className = "form-control missing-answer-input";
      input.dataset.key = q.field_key;
      input.placeholder = "Your answer (or leave blank if unsure)";
      wrap.appendChild(input);

      missingQuestionsList.appendChild(wrap);
    });

    clarificationSection.style.display = "block";
    setStep(2);
  }

  // Render Draft Response
  function displayDraftResponse(data) {
    state.currentDraftResponse = data;

    // Populate editable draft fields
    workerSummaryText.textContent = data.worker_summary_simple || "Summary prepared.";
    draftSubjectInput.value = data.subject_line || "Formal Grievance";
    draftBodyTextarea.value = data.grievance_draft || "";

    // Breakdown and Next Steps
    renderBreakdown(data.fact_status);
    renderNextSteps(data.worker_controlled_next_steps);

    // Missing Questions
    if (data.missing_questions && data.missing_questions.length > 0) {
      renderMissingQuestions(data.missing_questions);
    } else {
      clarificationSection.style.display = "none";
      setStep(3);
    }

    draftOutputSection.style.display = "block";
    draftOutputSection.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  // API Call: Intake / Draft
  async function submitDisputeIntake(additionalFacts = null) {
    clearError();
    const narrative = narrativeTextarea.value.trim();

    if (narrative.length < 10) {
      showError("Please describe what happened in at least 10 characters.");
      return;
    }

    btnSpinner.style.display = "inline-block";
    btnText.textContent = "Preparing Draft...";
    generateDraftBtn.disabled = true;

    const payload = {
      dispute_text: narrative,
      category: categorySelect.value,
      platform_or_employer: platformInput.value.trim() || null,
      worker_state: stateInput.value.trim() || null,
      preferred_language: preferredLangSelect.value,
      additional_facts: additionalFacts,
    };

    try {
      const response = await fetch("/api/v1/grievance/intake", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Server returned status ${response.status}`);
      }

      const data = await response.json();
      displayDraftResponse(data);
    } catch (err) {
      console.error("Dispute intake failure:", err);
      showError(err.message || "Failed to process grievance draft. Please verify your connection.");
    } finally {
      btnSpinner.style.display = "none";
      btnText.textContent = "Generate Grievance Draft";
      generateDraftBtn.disabled = false;
    }
  }

  // Event Listeners
  narrativeTextarea.addEventListener("input", updateCharCount);

  if (voiceRecordBtn) {
    voiceRecordBtn.addEventListener("click", () => {
      if (state.isRecording) {
        stopVoiceRecording();
      } else {
        startVoiceRecording();
      }
    });
  }

  if (audioReadoutBtn) {
    audioReadoutBtn.addEventListener("click", () => {
      const textToRead = workerSummaryText.textContent;
      toggleAudioReadout(textToRead);
    });
  }

  disputeForm.addEventListener("submit", (e) => {
    e.preventDefault();
    submitDisputeIntake();
  });

  updateDraftWithFactsBtn.addEventListener("click", () => {
    const answerInputs = document.querySelectorAll(".missing-answer-input");
    const additionalFacts = {};
    answerInputs.forEach((inp) => {
      const val = inp.value.trim();
      if (val) {
        additionalFacts[inp.dataset.key] = val;
      }
    });

    submitDisputeIntake(additionalFacts);
  });

  // Copy Draft to Clipboard
  copyDraftBtn.addEventListener("click", async () => {
    const fullText = `Subject: ${draftSubjectInput.value}\n\n${draftBodyTextarea.value}`;
    try {
      await navigator.clipboard.writeText(fullText);
      copyStatusMsg.textContent = "\u2714 Draft copied to clipboard!";
      setTimeout(() => {
        copyStatusMsg.textContent = "";
      }, 3500);
    } catch (err) {
      // Fallback for non-secure contexts
      draftBodyTextarea.select();
      document.execCommand("copy");
      copyStatusMsg.textContent = "\u2714 Draft copied!";
      setTimeout(() => {
        copyStatusMsg.textContent = "";
      }, 3500);
    }
  });

  // Download Draft as .txt file
  downloadDraftBtn.addEventListener("click", () => {
    const fullText = `Subject: ${draftSubjectInput.value}\n\n${draftBodyTextarea.value}\n\n---\nCreated with Gig-Aid (Worker-Controlled Grievance Assistant)`;
    const blob = new Blob([fullText], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "gig-aid-grievance-draft.txt";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });

  // Initial character count
  updateCharCount();
})();
