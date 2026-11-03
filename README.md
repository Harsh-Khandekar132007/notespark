# NoteSpark: Smart Notes-to-Flashcards & Quiz Generator

**NoteSpark** is an AI-powered web application that turns lengthy lecture notes, textbooks, and PDF documents into interactive revision materials—including 3D-flippable flashcards, customizable multiple-choice quizzes, AI summaries, and printable/exportable PDF revision guides.

---

## 🚀 Key Features

### Core Capabilities
- **Flexible Notes Input**: Upload PDF documents (`.pdf`), text files (`.txt`), or directly paste notes into the rich input area.
- **Robust Text Extraction**: Seamless document extraction powered by `PyPDF2` with `PyMuPDF` (fitz) fallback.
- **AI-Powered Generation**: Built with **Groq API** (`llama-3.3-70b-versatile` / `llama-3.1-8b-instant`) for near-instant exam-grade flashcards and quizzes.
- **Zero-Crash Fallback Generator**: Includes a built-in heuristic NLP generation engine if an API key is not yet configured or when offline.
- **Automatic Quiz Evaluation & Scoring**: Instant scoring, answer breakdown, and detailed explanations for every question.
- **Saved Study Materials**: Persistent SQLite database preserving study sets, progress, and review statuses.

### Advanced Capabilities
- **AI Notes Summarization**: High-yield summaries of key formulas, principles, and takeaways.
- **Adjustable Difficulty**: Select between **Easy** (factual recall), **Medium** (conceptual application), and **Hard** (critical evaluation/edge cases).
- **Topic-Focused Generation**: Specify an optional topic focus (e.g., *Round Robin Scheduling*, *Markovnikov Rule*, *Binary Search Trees*).
- **Interactive 3D Flashcards**: Flip cards, filter by subtopics, mark cards as *"Review again"* or *"Got it"*, and navigate using keyboard shortcuts (`Space`, `←`, `→`).
- **Quiz Performance Tracking**: Historical analytics, score progression bar charts, and AI-driven revision recommendations.
- **Export to PDF**: Generate clean, publication-grade revision sheets (with summary, flashcards table, quiz questions, and answer key) via `ReportLab`.

---

## 🛠️ Technology Stack
- **Backend**: Python 3.10+, Flask 3.0+
- **AI Engine**: Groq Cloud SDK (`llama-3.3-70b-versatile`)
- **Document Processing**: PyPDF2, PyMuPDF (fitz), ReportLab
- **Database**: SQLite3
- **Frontend**: Clean semantic HTML5, CSS3 with NoteSpark Design System (`Plus Jakarta Sans`), Vanilla JavaScript

---

## 📦 Quick Start Guide

### 1. Run the Application
Open a terminal in the project directory:
```bash
cd C:\Users\harsh\.gemini\antigravity\scratch\notespark
python app.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000
```

### 2. Configure Groq API Key (Optional but Recommended)
You can get a free, high-speed API key from [Groq Console](https://console.groq.com/keys).
- Click the **"API Settings"** button in the sidebar of the web app and paste your key.
- Alternatively, add it to your `.env` file:
  ```env
  GROQ_API_KEY=gsk_your_key_here
  ```

---

## 📁 Project Structure
```
notespark/
├── app.py                 # Flask server routes and API endpoints
├── config.py              # Environment configuration & paths
├── database.py            # SQLite schema, queries, and seed data
├── ai_service.py          # Groq API Llama-3 client & fallback generator
├── pdf_service.py         # PyPDF2 extraction and ReportLab PDF generator
├── requirements.txt       # Python dependencies
├── .env.example           # Example environment variables
├── static/
│   ├── css/
│   │   └── style.css      # Custom NoteSpark stylesheet
│   └── js/
│       ├── main.js        # Global utilities, upload drag-and-drop, settings
│       ├── flashcards.js  # 3D flip card player & topic filter
│       └── quiz.js        # Quiz runner, question navigator & scoring
└── templates/
    ├── base.html          # Shared layout and navigation sidebar
    ├── dashboard.html     # Dashboard with stats, recent sets, & chart
    ├── new_study_set.html # Upload & generation options
    ├── flashcards.html    # Interactive flashcards view & summary
    ├── quiz.html          # Interactive multiple-choice quiz
    ├── library.html       # Full library with search & management
    └── performance.html   # Detailed performance tracking & history
```
