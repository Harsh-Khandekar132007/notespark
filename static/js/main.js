// NoteSpark Core Utilities & Global Handlers

function showToast(message, type = 'normal') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.25s ease';
    setTimeout(() => toast.remove(), 250);
  }, 3500);
}

// Settings Modal for Groq API Key
function openSettingsModal() {
  const modal = document.getElementById('settings-modal');
  if (modal) {
    modal.classList.add('active');
    loadCurrentApiKey();
  }
}

function closeSettingsModal() {
  const modal = document.getElementById('settings-modal');
  if (modal) {
    modal.classList.remove('active');
  }
}

async function loadCurrentApiKey() {
  try {
    const res = await fetch('/api/settings/groq-key');
    const data = await res.json();
    const input = document.getElementById('groq-api-key-input');
    const modelInput = document.getElementById('groq-model-input');
    const statusText = document.getElementById('api-key-status');
    if (input) {
      input.value = data.key || '';
    }
    if (modelInput && data.model) {
      modelInput.value = data.model;
    }
    if (statusText) {
      if (data.is_set) {
        statusText.innerHTML = `<span style="color:#059669;font-weight:600;">✓ Active key configured (${data.preview}) - ${data.model}</span>`;
      } else {
        statusText.innerHTML = `<span style="color:#D97706;font-weight:500;">No Groq API key set. App using high-quality local NLP generator.</span>`;
      }
    }
  } catch (err) {
    console.error('Failed to load API key setting', err);
  }
}

async function saveGroqApiKey(e) {
  if (e) e.preventDefault();
  const input = document.getElementById('groq-api-key-input');
  const modelInput = document.getElementById('groq-model-input');
  const btn = document.getElementById('save-key-btn');
  if (!input) return;

  const newKey = input.value.trim();
  const newModel = modelInput ? modelInput.value : 'openai/gpt-oss-120b';
  if (btn) btn.disabled = true;

  try {
    const res = await fetch('/api/settings/groq-key', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key: newKey, model: newModel })
    });
    const data = await res.json();
    if (data.success) {
      showToast('Groq settings saved successfully!', 'success');
      closeSettingsModal();
      // Update badge if exists
      const badge = document.getElementById('sidebar-api-badge');
      if (badge) {
        if (newKey) {
          const modelShort = newModel.includes('120b') ? '120B Flagship' : (newModel.includes('27b') ? '27B Precision' : '20B Fast');
          badge.className = 'api-badge online';
          badge.innerHTML = `<span>AI Engine</span><span style="color:#059669">● ${modelShort} (Groq)</span>`;
        } else {
          badge.className = 'api-badge';
          badge.innerHTML = '<span>AI Engine</span><span style="color:#D97706">● Local NLP</span>';
        }
      }
    } else {
      showToast(data.error || 'Failed to save settings', 'error');
    }
  } catch (err) {
    showToast('Network error while saving settings', 'error');
  } finally {
    if (btn) btn.disabled = false;
  }
}

// Delete study set confirmation
async function confirmDeleteSet(setId, setTitle) {
  if (confirm(`Are you sure you want to delete "${setTitle}"? This will delete all flashcards, quizzes, and history for this set.`)) {
    try {
      const res = await fetch(`/api/study-set/${setId}/delete`, {
        method: 'POST'
      });
      const data = await res.json();
      if (data.success) {
        showToast('Study set deleted', 'normal');
        setTimeout(() => window.location.reload(), 400);
      } else {
        showToast('Error deleting study set', 'error');
      }
    } catch (err) {
      showToast('Request failed', 'error');
    }
  }
}

// New Study Set Form Logic
document.addEventListener('DOMContentLoaded', () => {
  const fileInput = document.getElementById('file-upload-input');
  const dropZone = document.getElementById('file-drop-zone');
  const chosenFileContainer = document.getElementById('file-chosen-container');
  const generateForm = document.getElementById('generate-study-set-form');
  const generateBtn = document.getElementById('generate-btn');

  if (dropZone && fileInput) {
    dropZone.addEventListener('click', () => fileInput.click());

    ['dragenter', 'dragover'].forEach(eventName => {
      dropZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
      }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
      dropZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
      }, false);
    });

    dropZone.addEventListener('drop', (e) => {
      const dt = e.dataTransfer;
      const files = dt.files;
      if (files.length > 0) {
        fileInput.files = files;
        updateSelectedFileName(files[0].name);
      }
    });

    fileInput.addEventListener('change', () => {
      if (fileInput.files.length > 0) {
        updateSelectedFileName(fileInput.files[0].name);
      }
    });
  }

  function updateSelectedFileName(name) {
    if (chosenFileContainer) {
      chosenFileContainer.innerHTML = `
        <div class="file-chosen-tag">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>
          <span>${name}</span>
          <button type="button" onclick="clearSelectedFile(event)" style="background:none;border:none;cursor:pointer;color:inherit;font-weight:bold;margin-left:4px;">×</button>
        </div>
      `;
    }
  }

  window.clearSelectedFile = function(e) {
    if (e) e.stopPropagation();
    if (fileInput) fileInput.value = '';
    if (chosenFileContainer) chosenFileContainer.innerHTML = '';
  };

  // Form submission via AJAX to show generation progress
  if (generateForm) {
    generateForm.addEventListener('submit', async (e) => {
      e.preventDefault();

      const notesText = document.getElementById('notes')?.value.trim() || '';
      const hasFile = fileInput && fileInput.files && fileInput.files.length > 0;

      if (!notesText && !hasFile) {
        showToast('Please upload a PDF/TXT file or paste your notes to generate a study set.', 'error');
        return;
      }

      // Check create options
      const optFlashcards = document.getElementById('o1')?.checked;
      const optQuiz = document.getElementById('o2')?.checked;
      const optSummary = document.getElementById('o3')?.checked;

      if (!optFlashcards && !optQuiz && !optSummary) {
        showToast('Please select at least one item to create (Flashcards, Quiz, or Summary).', 'error');
        return;
      }

      const formData = new FormData(generateForm);
      if (generateBtn) {
        generateBtn.disabled = true;
        generateBtn.innerHTML = `<div class="spinner"></div> Generating study set with AI...`;
      }

      try {
        const res = await fetch('/api/generate', {
          method: 'POST',
          body: formData
        });
        const data = await res.json();
        if (data.success) {
          showToast(data.message || 'Study set generated successfully!', 'success');
          // Navigate to flashcards or quiz
          setTimeout(() => {
            if (data.has_flashcards) {
              window.location.href = `/study/${data.study_set_id}/flashcards`;
            } else if (data.has_quiz) {
              window.location.href = `/study/${data.study_set_id}/quiz`;
            } else {
              window.location.href = `/study/${data.study_set_id}/flashcards`;
            }
          }, 600);
        } else {
          showToast(data.error || 'Failed to generate study set', 'error');
          if (generateBtn) {
            generateBtn.disabled = false;
            generateBtn.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M13 2L4 14h7l-1 8 9-12h-7z"></path></svg>Generate study set`;
          }
        }
      } catch (err) {
        showToast('Connection error during generation. Please try again.', 'error');
        if (generateBtn) {
          generateBtn.disabled = false;
          generateBtn.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M13 2L4 14h7l-1 8 9-12h-7z"></path></svg>Generate study set`;
        }
      }
    });
  }
});
