// NoteSpark Interactive Flashcards Controller

let allCards = [];
let filteredCards = [];
let currentIndex = 0;
let isFlipped = false;
let currentStudySetId = null;

function initFlashcards(cardsData, setId) {
  allCards = cardsData || [];
  filteredCards = [...allCards];
  currentStudySetId = setId;
  currentIndex = 0;
  isFlipped = false;

  renderCurrentCard();
  setupKeyboardNavigation();
}

function filterByTopic(topic, element) {
  // Update topic pill styles
  document.querySelectorAll('.topic-pill').forEach(el => el.classList.remove('active'));
  if (element) element.classList.add('active');

  if (!topic || topic.toLowerCase() === 'all') {
    filteredCards = [...allCards];
  } else {
    filteredCards = allCards.filter(c => (c.topic || '').toLowerCase() === topic.toLowerCase());
  }

  currentIndex = 0;
  isFlipped = false;
  renderCurrentCard();
}

function flipCard() {
  const cardElem = document.getElementById('flashcard-3d');
  if (!cardElem) return;

  isFlipped = !isFlipped;
  if (isFlipped) {
    cardElem.classList.add('flipped');
  } else {
    cardElem.classList.remove('flipped');
  }
}

function nextCard() {
  if (filteredCards.length === 0) return;
  currentIndex = (currentIndex + 1) % filteredCards.length;
  resetFlipAndRender();
}

function prevCard() {
  if (filteredCards.length === 0) return;
  currentIndex = (currentIndex - 1 + filteredCards.length) % filteredCards.length;
  resetFlipAndRender();
}

function resetFlipAndRender() {
  const cardElem = document.getElementById('flashcard-3d');
  if (cardElem) {
    cardElem.classList.remove('flipped');
  }
  isFlipped = false;
  renderCurrentCard();
}

function renderCurrentCard() {
  const progressText = document.getElementById('card-progress-text');
  const progressBar = document.getElementById('card-progress-fill');
  const qText = document.getElementById('card-question-text');
  const aText = document.getElementById('card-answer-text');
  const topicTag = document.getElementById('card-topic-tag');

  if (filteredCards.length === 0) {
    if (progressText) progressText.innerText = "0 of 0 cards";
    if (progressBar) progressBar.style.width = "0%";
    if (qText) qText.innerText = "No flashcards found for this topic.";
    if (aText) aText.innerText = "Select 'All' to view all cards.";
    return;
  }

  const card = filteredCards[currentIndex];
  const total = filteredCards.length;
  const currentNum = currentIndex + 1;
  const percent = Math.round((currentNum / total) * 100);

  if (progressText) progressText.innerText = `Card ${currentNum} of ${total}`;
  if (progressBar) progressBar.style.width = `${percent}%`;
  if (qText) qText.innerText = card.question || '';
  if (aText) aText.innerText = card.answer || '';
  if (topicTag) topicTag.innerText = card.topic || 'General';
}

// Mark status ('got_it' or 'review_again')
async function markCardStatus(status) {
  if (filteredCards.length === 0) return;
  const card = filteredCards[currentIndex];
  card.status = status;

  try {
    fetch(`/api/card/${card.id}/status`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status })
    });
  } catch (err) {
    console.error('Error saving card status', err);
  }

  if (status === 'got_it') {
    showToast('Marked as mastered!', 'success');
  } else {
    showToast('Saved for review again', 'normal');
  }

  // Advance to next card smoothly
  setTimeout(() => {
    nextCard();
  }, 200);
}

// Keyboard shortcuts
function setupKeyboardNavigation() {
  document.addEventListener('keydown', (e) => {
    // Ignore if typing in an input or textarea
    if (['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;

    if (e.code === 'Space') {
      e.preventDefault();
      flipCard();
    } else if (e.code === 'ArrowRight') {
      e.preventDefault();
      nextCard();
    } else if (e.code === 'ArrowLeft') {
      e.preventDefault();
      prevCard();
    } else if (e.key === '1' || e.key.toLowerCase() === 'r') {
      markCardStatus('review_again');
    } else if (e.key === '2' || e.key.toLowerCase() === 'g') {
      markCardStatus('got_it');
    }
  });
}
