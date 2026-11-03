// NoteSpark Interactive Quiz Controller

let quizQuestions = [];
let userSelections = {}; // questionIndex -> selectedOptionIndex
let quizIndex = 0;
let currentStudySetId = null;
let isQuizReviewed = false;
let quizResultData = null;

function initQuiz(questionsData, setId) {
  quizQuestions = questionsData || [];
  currentStudySetId = setId;
  userSelections = {};
  quizIndex = 0;
  isQuizReviewed = false;
  quizResultData = null;

  renderQuizQuestion();
  renderNavigatorGrid();
}

function selectOption(optIndex) {
  if (isQuizReviewed) return; // Read-only in review mode
  userSelections[quizIndex] = optIndex;

  // Re-render current question and navigator
  renderQuizQuestion();
  renderNavigatorGrid();
}

function goToQuestion(index) {
  if (index >= 0 && index < quizQuestions.length) {
    quizIndex = index;
    renderQuizQuestion();
    renderNavigatorGrid();
  }
}

function nextQuestion() {
  if (quizIndex < quizQuestions.length - 1) {
    quizIndex++;
    renderQuizQuestion();
    renderNavigatorGrid();
  }
}

function prevQuestion() {
  if (quizIndex > 0) {
    quizIndex--;
    renderQuizQuestion();
    renderNavigatorGrid();
  }
}

function renderQuizQuestion() {
  if (quizQuestions.length === 0) return;

  const q = quizQuestions[quizIndex];
  const total = quizQuestions.length;
  const currentNum = quizIndex + 1;
  const progressPercent = Math.round((currentNum / total) * 100);

  // Update headers
  const subtitle = document.getElementById('quiz-question-counter');
  if (subtitle) subtitle.innerText = `Question ${currentNum} of ${total}`;

  const diffBadge = document.getElementById('quiz-diff-badge');
  if (diffBadge) diffBadge.innerText = q.difficulty || 'Medium';

  const topicBadge = document.getElementById('quiz-topic-badge');
  if (topicBadge) topicBadge.innerText = q.topic || 'General';

  const progressBar = document.getElementById('quiz-progress-fill');
  if (progressBar) progressBar.style.width = `${progressPercent}%`;

  const questionTitle = document.getElementById('quiz-question-title');
  if (questionTitle) questionTitle.innerText = q.question || '';

  // Render options
  const optionsContainer = document.getElementById('quiz-options-container');
  if (optionsContainer) {
    optionsContainer.innerHTML = '';
    const selectedOpt = userSelections[quizIndex];

    (q.options || []).forEach((optText, idx) => {
      const isSelected = selectedOpt === idx;
      let reviewClass = '';

      if (isQuizReviewed) {
        if (idx === q.correct_index) {
          reviewClass = 'correct-review';
        } else if (isSelected && idx !== q.correct_index) {
          reviewClass = 'wrong-review';
        }
      }

      const label = document.createElement('label');
      label.className = `quiz-option-label ${isSelected ? 'selected' : ''} ${reviewClass}`;
      label.onclick = () => selectOption(idx);

      label.innerHTML = `
        <input type="radio" name="quiz_opt_${quizIndex}" value="${idx}" ${isSelected ? 'checked' : ''} class="quiz-option-input" ${isQuizReviewed ? 'disabled' : ''}>
        <span>${escapeHtml(optText)}</span>
      `;
      optionsContainer.appendChild(label);
    });

    // If in review mode, show explanation box
    const explBox = document.getElementById('quiz-explanation-box');
    if (explBox) {
      if (isQuizReviewed) {
        const isCorrect = selectedOpt === q.correct_index;
        explBox.style.display = 'block';
        explBox.innerHTML = `
          <div style="margin-top:16px;padding:16px;border-radius:12px;background:${isCorrect ? '#ECFDF5' : '#FEF2F2'};border:1px solid ${isCorrect ? '#10B981' : '#F87171'}">
            <div style="font-weight:700;font-size:14px;color:${isCorrect ? '#065F46' : '#991B1B'};margin-bottom:4px;">
              ${isCorrect ? '✓ Correct Answer' : '✗ Incorrect Answer'} (Option ${String.fromCharCode(65 + q.correct_index)})
            </div>
            <div style="font-size:14px;color:#141A2E;line-height:1.45;">
              ${escapeHtml(q.explanation || 'No explanation provided.')}
            </div>
          </div>
        `;
      } else {
        explBox.style.display = 'none';
      }
    }
  }

  // Update Next / Prev buttons
  const prevBtn = document.getElementById('quiz-prev-btn');
  const nextBtn = document.getElementById('quiz-next-btn');

  if (prevBtn) prevBtn.disabled = quizIndex === 0;
  if (nextBtn) {
    if (quizIndex === total - 1) {
      nextBtn.innerText = isQuizReviewed ? "Finished Review" : "Finish & Submit";
      nextBtn.onclick = isQuizReviewed ? () => openResultModal() : submitQuiz;
    } else {
      nextBtn.innerText = "Next question";
      nextBtn.onclick = nextQuestion;
    }
  }
}

function renderNavigatorGrid() {
  const grid = document.getElementById('quiz-nav-grid');
  if (!grid || quizQuestions.length === 0) return;

  grid.innerHTML = '';
  quizQuestions.forEach((q, idx) => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'q-nav-btn';
    btn.innerText = idx + 1;
    btn.setAttribute('aria-label', `Question ${idx + 1}`);

    const isAnswered = userSelections[idx] !== undefined;
    const isActive = quizIndex === idx;

    if (isQuizReviewed) {
      const isCorrect = userSelections[idx] === q.correct_index;
      if (isCorrect) {
        btn.classList.add('review-correct');
      } else {
        btn.classList.add('review-wrong');
      }
    } else {
      if (isActive) {
        btn.classList.add('active');
      } else if (isAnswered) {
        btn.classList.add('answered');
      }
    }

    btn.onclick = () => goToQuestion(idx);
    grid.appendChild(btn);
  });
}

async function submitQuiz() {
  if (isQuizReviewed) {
    openResultModal();
    return;
  }

  const total = quizQuestions.length;
  const answeredCount = Object.keys(userSelections).length;

  if (answeredCount < total) {
    const remaining = total - answeredCount;
    if (!confirm(`You still have ${remaining} unanswered question(s). Submit quiz anyway?`)) {
      return;
    }
  }

  const submitBtn = document.getElementById('quiz-submit-sidebar-btn');
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerText = "Calculating score...";
  }

  try {
    const res = await fetch(`/api/quiz/${currentStudySetId}/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ answers: userSelections })
    });
    const data = await res.json();
    if (data.success) {
      quizResultData = data;
      isQuizReviewed = true;
      openResultModal();
      renderQuizQuestion();
      renderNavigatorGrid();
    } else {
      showToast(data.error || 'Failed to submit quiz', 'error');
    }
  } catch (err) {
    showToast('Network error submitting quiz', 'error');
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerText = "View Results";
      submitBtn.onclick = openResultModal;
    }
  }
}

function openResultModal() {
  const modal = document.getElementById('quiz-result-modal');
  if (!modal || !quizResultData) return;

  const scoreVal = document.getElementById('result-score-val');
  const scoreDesc = document.getElementById('result-score-desc');
  const badgeTitle = document.getElementById('result-badge-title');

  const pct = quizResultData.score_percentage || 0;
  const correct = quizResultData.correct_count || 0;
  const total = quizResultData.total_questions || quizQuestions.length;

  if (scoreVal) scoreVal.innerText = `${pct}%`;
  if (scoreDesc) scoreDesc.innerText = `You answered ${correct} out of ${total} questions correctly.`;

  if (badgeTitle) {
    if (pct >= 85) {
      badgeTitle.innerText = "Outstanding Mastery! 🏆";
      badgeTitle.style.color = "#059669";
    } else if (pct >= 70) {
      badgeTitle.innerText = "Great Job! 🎉";
      badgeTitle.style.color = "#4338CA";
    } else if (pct >= 50) {
      badgeTitle.innerText = "Good Effort! 👍";
      badgeTitle.style.color = "#D97706";
    } else {
      badgeTitle.innerText = "Keep Practicing! 📚";
      badgeTitle.style.color = "#DC2626";
    }
  }

  modal.classList.add('active');
}

function closeResultModal() {
  const modal = document.getElementById('quiz-result-modal');
  if (modal) modal.classList.remove('active');
}

function reviewQuizAnswers() {
  closeResultModal();
  goToQuestion(0);
  showToast('Reviewing answers: Green indicates correct, Red indicates your selection.', 'normal');
}

function retakeQuiz() {
  if (confirm('Retake this quiz? Your previous attempt has been saved to Performance.')) {
    userSelections = {};
    isQuizReviewed = false;
    quizResultData = null;
    closeResultModal();
    quizIndex = 0;
    renderQuizQuestion();
    renderNavigatorGrid();

    const submitBtn = document.getElementById('quiz-submit-sidebar-btn');
    if (submitBtn) {
      submitBtn.innerText = "Submit quiz";
      submitBtn.onclick = submitQuiz;
    }
    showToast('Quiz reset. Good luck!', 'success');
  }
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.innerText = text;
  return div.innerHTML;
}
