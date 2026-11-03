import json
import os
import re
import random
import unicodedata
from config import Config
from database import get_app_setting

def get_active_groq_api_key():
    """Retrieves Groq API key from database settings or environment."""
    saved_key = get_app_setting('groq_api_key')
    if saved_key and saved_key.strip():
        return saved_key.strip()
    env_key = os.environ.get('GROQ_API_KEY', '')
    if env_key and env_key.strip():
        return env_key.strip()
    return Config.GROQ_API_KEY.strip()

def get_active_groq_model():
    """Retrieves selected Groq model from database or config."""
    saved_model = get_app_setting('groq_model')
    if saved_model and saved_model.strip():
        return saved_model.strip()
    return os.environ.get('GROQ_MODEL', Config.GROQ_MODEL)

def sanitize_ai_text(text):
    """Normalizes Unicode characters, non-breaking hyphens, and smart quotes."""
    if not text:
        return ""
    # Normalize unicode
    text = unicodedata.normalize('NFKD', text)
    replacements = {
        '\u2011': '-',
        '\u2010': '-',
        '\u2012': '-',
        '\u2013': '-',
        '\u2014': '--',
        '\u2018': "'",
        '\u2019': "'",
        '\u201c': '"',
        '\u201d': '"',
        '\u00a0': ' ',
        '\u202f': ' ',
        '\u2026': '...'
    }
    for orig, rep in replacements.items():
        text = text.replace(orig, rep)
    # Ensure it's encodable in standard environments
    try:
        text = text.encode('ascii', 'ignore').decode('ascii')
    except Exception:
        pass
    return text.strip()

def generate_study_material(raw_text, create_flashcards=True, create_quiz=True, create_summary=True, 
                            difficulty='Medium', topic_focus='', question_count=10, model_name=None):
    """
    Primary AI generation pipeline.
    Uses high-capacity Groq models (120B / 27B) with academic prompt engineering.
    Falls back gracefully to alternative Groq models or local rule-based NLP if needed.
    """
    api_key = get_active_groq_api_key()
    chosen_model = model_name or get_active_groq_model()
    
    # Priority cascade of supported Groq models
    models_to_try = [chosen_model]
    for backup in ['openai/gpt-oss-120b', 'qwen/qwen3.8-27b', 'openai/gpt-oss-20b']:
        if backup not in models_to_try:
            models_to_try.append(backup)

    if api_key:
        for model in models_to_try:
            try:
                print(f"Executing AI generation with model: {model}")
                result = call_groq_api(
                    api_key=api_key,
                    model_name=model,
                    raw_text=raw_text,
                    create_flashcards=create_flashcards,
                    create_quiz=create_quiz,
                    create_summary=create_summary,
                    difficulty=difficulty,
                    topic_focus=topic_focus,
                    question_count=question_count
                )
                if result and (result.get('flashcards') or result.get('quiz')):
                    result['generator_type'] = 'groq'
                    result['model_used'] = model
                    return result
            except Exception as e:
                print(f"Model {model} generation notice: {e}")

    # Fallback generator if Groq is unavailable
    print("Falling back to internal rule-based generator.")
    fallback_result = generate_fallback_study_material(
        raw_text=raw_text,
        create_flashcards=create_flashcards,
        create_quiz=create_quiz,
        create_summary=create_summary,
        difficulty=difficulty,
        topic_focus=topic_focus,
        question_count=question_count
    )
    fallback_result['generator_type'] = 'fallback'
    fallback_result['model_used'] = 'Internal Rule-Based Generator'
    return fallback_result

def call_groq_api(api_key, model_name, raw_text, create_flashcards, create_quiz, create_summary, 
                  difficulty, topic_focus, question_count):
    """Invokes Groq API with academic exam-prep prompt engineering."""
    import groq
    client = groq.Groq(api_key=api_key)

    clean_input = sanitize_ai_text(raw_text[:20000])

    system_instruction = (
        "You are NoteSpark, an elite university professor and test design specialist. "
        "Your task is to transform study notes into rigorous, exam-grade revision materials. "
        "Strict rules:\n"
        "1. Never create basic, one-word, or trivial recall questions.\n"
        "2. Flashcards must test underlying mechanisms, trade-offs, comparisons, and causal relationships.\n"
        "3. Multiple-choice questions (MCQs) must be analytical or scenario-based, aligned with university/competitive exam standards.\n"
        "4. Options MUST contain exactly 4 choices (strings) with subtle, plausible distractors reflecting common student misconceptions. Never use 'All of the above' or 'None of the above'.\n"
        "5. Correct index must be an integer from 0 to 3.\n"
        "6. Provide a thorough, educational explanation for every question.\n"
        "7. Output ONLY valid JSON matching the requested schema."
    )

    requirements = []
    if create_summary:
        requirements.append("Generate a high-yield 'summary' (3-5 comprehensive sentences) synthesizing key principles and formulas.")
    if create_flashcards:
        target_card_count = min(15, max(8, question_count * 2))
        requirements.append(
            f"Generate exactly {target_card_count} probing 'flashcards'. Fronts must test conceptual understanding (e.g. 'How does X differ from Y?', 'Why does X happen instead of Y?')."
        )
    if create_quiz:
        requirements.append(
            f"Generate exactly {question_count} challenging multiple-choice 'quiz' questions at the '{difficulty}' difficulty level with 4 plausible options, correct_index (0-3), and thorough explanation."
        )

    difficulty_context = {
        "Easy": "Fundamental principles, core definitions, and distinct conceptual mechanisms.",
        "Medium": "Multi-step analytical reasoning, comparative trade-offs, and practical scenario application.",
        "Hard": "Rigorous edge cases, mathematical or algorithmic calculations, subtle distractor traps, and deep evaluation."
    }.get(difficulty, "Exam standard.")

    topic_instruction = f"Priority Topic Focus: '{topic_focus}'. Focus heavily on this area." if topic_focus else ""

    user_prompt = f"""Generate an exam-ready study set from the provided notes in strict JSON format.

DIFFICULTY LEVEL: {difficulty} ({difficulty_context})
{topic_instruction}

SCHEMA:
{{
  "title": "Clear, descriptive title for the study set",
  "summary": "3-5 sentence academic summary of the notes...",
  "topics": ["Topic 1", "Topic 2", "Topic 3"],
  "flashcards": [
    {{
      "question": "Probing, conceptual question",
      "answer": "Definitive explanation and rationale",
      "topic": "Specific Topic"
    }}
  ],
  "quiz": [
    {{
      "question": "Scenario or problem-solving question?",
      "options": ["Distractor A", "Correct Answer B", "Distractor C", "Distractor D"],
      "correct_index": 1,
      "explanation": "Detailed explanation of why B is correct and others are flawed.",
      "topic": "Specific Topic",
      "difficulty": "{difficulty}"
    }}
  ]
}}

REQUIREMENTS:
{chr(10).join('- ' + r for r in requirements)}

STUDY NOTES:
\"\"\"
{clean_input}
\"\"\"
"""

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.2,
        max_tokens=4000,
        response_format={"type": "json_object"}
    )

    raw_content = response.choices[0].message.content
    cleaned_content = sanitize_ai_text(raw_content)
    data = json.loads(cleaned_content)
    
    if not data.get('title'):
        data['title'] = infer_title_from_text(raw_text, topic_focus)
    if 'flashcards' not in data:
        data['flashcards'] = []
    if 'quiz' not in data:
        data['quiz'] = []
        
    for c in data['flashcards']:
        c['question'] = sanitize_ai_text(c.get('question', ''))
        c['answer'] = sanitize_ai_text(c.get('answer', ''))
        c['topic'] = sanitize_ai_text(c.get('topic', 'General'))

    valid_quiz = []
    for q in data['quiz']:
        q['question'] = sanitize_ai_text(q.get('question', ''))
        q['options'] = [sanitize_ai_text(opt) for opt in q.get('options', [])]
        q['explanation'] = sanitize_ai_text(q.get('explanation', ''))
        q['topic'] = sanitize_ai_text(q.get('topic', 'General'))
        q['difficulty'] = q.get('difficulty', difficulty)

        try:
            q['correct_index'] = int(q.get('correct_index', 0))
            if q['correct_index'] < 0 or q['correct_index'] >= len(q['options']):
                q['correct_index'] = 0
        except (ValueError, TypeError):
            q['correct_index'] = 0

        if len(q['options']) == 4 and q['question']:
            valid_quiz.append(q)

    data['quiz'] = valid_quiz
    if 'summary' not in data or not data['summary']:
        data['summary'] = generate_simple_summary(raw_text)
    else:
        data['summary'] = sanitize_ai_text(data['summary'])

    if 'topics' not in data or not data['topics']:
        data['topics'] = list(set([c.get('topic', 'General') for c in data['flashcards']] + [q.get('topic', 'General') for q in data['quiz']]))
        
    return data

def infer_title_from_text(text, topic_focus=""):
    if topic_focus and len(topic_focus.strip()) > 2:
        return topic_focus.strip().title()
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if lines:
        first_line = lines[0]
        first_line = re.sub(r'^[#*_\-0-9. ]+', '', first_line).strip()
        if 5 <= len(first_line) <= 60:
            return first_line.title()
    return "Study Notes & Revision Set"

def generate_simple_summary(text):
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    meaningful = [s.strip() for s in sentences if len(s.strip()) > 30 and not s.strip().startswith(('Chapter', 'Page', 'Figure'))]
    if meaningful:
        return " ".join(meaningful[:3])
    return text[:250].strip() + "..."

def generate_fallback_study_material(raw_text, create_flashcards=True, create_quiz=True, create_summary=True,
                                     difficulty='Medium', topic_focus='', question_count=10):
    """
    Enhanced NLP & pattern-based generator when Groq is not configured or offline.
    Extracts definitions, key terms, facts, comparisons, and constructs MCQs with smart distractors.
    """
    title = infer_title_from_text(raw_text, topic_focus)
    clean_text = sanitize_ai_text(raw_text.strip())
    
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', clean_text) if len(s.strip()) > 20]
    
    def_patterns = [
        r'^(?:An?|The)?\s*([A-Za-z0-9\- ]{3,35})\s+(?:is|are|refers to|means|defines|represents)\s+(.+)$',
        r'^(?:An?|The)?\s*([A-Za-z0-9\- ]{3,35})\s*[:\-–]\s*(.+)$',
        r'^(?:An?|The)?\s*([A-Za-z0-9\- ]{3,35})\s+(?:consists of|includes|deals with)\s+(.+)$'
    ]
    
    term_def_pairs = []
    seen_terms = set()
    
    for s in sentences:
        s_clean = s.strip().rstrip('.')
        for pat in def_patterns:
            m = re.match(pat, s_clean, re.I)
            if m:
                term = m.group(1).strip()
                desc = m.group(2).strip()
                if len(term) >= 3 and len(desc) >= 15 and term.lower() not in seen_terms:
                    seen_terms.add(term.lower())
                    term_def_pairs.append((term, desc, s))
                break

    if len(term_def_pairs) < 10:
        for idx, s in enumerate(sentences):
            words = s.split()
            if len(words) >= 6:
                first_part = " ".join(words[:4])
                first_part_clean = re.sub(r'[^a-zA-Z0-9 ]', '', first_part).strip()
                if first_part_clean and first_part_clean.lower() not in seen_terms:
                    seen_terms.add(first_part_clean.lower())
                    term_def_pairs.append((first_part_clean, s, s))

    default_topics = ["Core Concepts", "Key Principles", "Mechanisms", "Applications"]
    if topic_focus:
        default_topics.insert(0, topic_focus.strip().title())

    flashcards = []
    if create_flashcards:
        for idx, (term, desc, full_s) in enumerate(term_def_pairs):
            topic = default_topics[idx % len(default_topics)]
            if idx % 3 == 0:
                q = f"How does {term} function and what is its primary role?"
                a = f"{term} is characterized by: {desc.capitalize()}" + ("." if not desc.endswith(".") else "")
            elif idx % 3 == 1:
                q = f"What is the core significance of {term}?"
                a = full_s + ("." if not full_s.endswith(".") else "")
            else:
                q = f"Define {term} and state its key property:"
                a = desc.capitalize() + ("." if not desc.endswith(".") else "")
                
            flashcards.append({
                "question": q,
                "answer": a,
                "topic": topic
            })

    if len(flashcards) < 10:
        paras = [p.strip() for p in clean_text.split('\n\n') if len(p.strip()) > 40]
        for idx, p in enumerate(paras[:12]):
            s_list = re.split(r'(?<=[.!?])\s+', p)
            if len(s_list) >= 2:
                flashcards.append({
                    "question": f"Key takeaway regarding: {s_list[0][:60]}...",
                    "answer": " ".join(s_list[1:3]),
                    "topic": default_topics[idx % len(default_topics)]
                })

    quiz = []
    if create_quiz and term_def_pairs:
        all_terms = [t for t, d, s in term_def_pairs]
        all_descs = [d for t, d, s in term_def_pairs]
        
        target_q_count = min(question_count, max(5, len(term_def_pairs)))
        
        for q_idx in range(target_q_count):
            target_term, target_desc, target_sent = term_def_pairs[q_idx % len(term_def_pairs)]
            topic = default_topics[q_idx % len(default_topics)]
            
            if difficulty == "Hard":
                q_text = f"In evaluating the underlying mechanism of {target_term}, which statement is conceptually accurate?"
                correct_opt = f"It specifically governs: {target_desc[:90]}" + ("..." if len(target_desc) > 90 else "")
                distractors = [f"It acts conversely to {d[:80]}..." for d in all_descs if d.lower() != target_desc.lower()]
                while len(distractors) < 3:
                    distractors.append(f"It functions as a static protocol without dynamic feedback.")
                random.shuffle(distractors)
                selected_distractors = distractors[:3]
                
            elif difficulty == "Easy":
                q_text = f"Which concept is defined as: \"{target_desc[:120]}...\"?" if len(target_desc) > 80 else f"Which concept is defined as: \"{target_desc}\"?"
                correct_opt = target_term
                distractors = [t for t in all_terms if t.lower() != target_term.lower()]
                while len(distractors) < 3:
                    distractors.append(f"Alternative Concept {len(distractors) + 1}")
                random.shuffle(distractors)
                selected_distractors = distractors[:3]
                
            else: # Medium
                q_text = f"Which of the following best characterizes the function of {target_term}?"
                correct_opt = target_desc[:100] + ("..." if len(target_desc) > 100 else "")
                distractors = [d[:100] + "..." for d in all_descs if d.lower() != target_desc.lower()]
                while len(distractors) < 3:
                    distractors.append(f"An auxiliary process that executes only during terminal state transitions.")
                random.shuffle(distractors)
                selected_distractors = distractors[:3]

            options = [correct_opt] + selected_distractors
            random.shuffle(options)
            c_idx = options.index(correct_opt)
            
            explanation = f"Correct. {target_term} corresponds to: {target_desc[:140]}."
            
            quiz.append({
                "question": q_text,
                "options": options,
                "correct_index": c_idx,
                "explanation": explanation,
                "topic": topic,
                "difficulty": difficulty
            })

    summary = generate_simple_summary(clean_text) if create_summary else ""
    
    unique_topics = list(set([c['topic'] for c in flashcards] + [q['topic'] for q in quiz]))
    if not unique_topics:
        unique_topics = default_topics

    return {
        "title": title,
        "summary": summary,
        "topics": unique_topics,
        "flashcards": flashcards,
        "quiz": quiz
    }
