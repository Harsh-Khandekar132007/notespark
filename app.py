import os
import json
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file, flash
from werkzeug.utils import secure_filename

from config import Config
from database import (
    init_db, get_all_study_sets, get_study_set, get_flashcards, get_distinct_topics,
    get_quiz_questions, create_study_set, add_flashcards, add_quiz_questions,
    save_quiz_attempt, get_recent_attempts, get_overall_stats, delete_study_set,
    update_card_status, get_app_setting, set_app_setting, get_db_connection,
    get_performance_data
)
from pdf_service import extract_text_from_pdf, extract_text_from_txt, export_study_set_to_pdf
from ai_service import generate_study_material, get_active_groq_api_key, get_active_groq_model

app = Flask(__name__)
app.config.from_object(Config)

# Ensure upload and export directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['EXPORT_FOLDER'], exist_ok=True)

# Initialize database and seed sample data
init_db()

@app.context_processor
def inject_global_vars():
    groq_key = get_active_groq_api_key()
    groq_model = get_active_groq_model()
    return {
        'has_groq_key': bool(groq_key),
        'groq_model': groq_model
    }

# ==================== Page Routes ====================

@app.route('/')
def dashboard():
    stats = get_overall_stats()
    all_sets = get_all_study_sets()
    recent_sets = all_sets[:4]

    # Real quiz attempts for the last 6 bars
    recent_attempts = get_recent_attempts(limit=6)
    chart_attempts = []
    
    if recent_attempts:
        for idx, att in enumerate(recent_attempts, start=1):
            pct = att['score_percentage']
            color = '#10B981' if pct >= 80 else ('#F59E0B' if pct >= 60 else '#EF4444')
            chart_attempts.append({
                'label': f"T{idx}",
                'pct': pct,
                'title': att.get('set_title', 'Quiz'),
                'color': color
            })

    return render_template(
        'dashboard.html',
        active_page='dashboard',
        stats=stats,
        recent_sets=recent_sets,
        chart_attempts=chart_attempts
    )

@app.route('/new')
def new_study_set():
    return render_template('new_study_set.html', active_page='new_set')

@app.route('/study/<int:set_id>/flashcards')
def view_flashcards(set_id):
    study_set = get_study_set(set_id)
    if not study_set:
        return redirect(url_for('dashboard'))

    cards = get_flashcards(set_id)
    topics = get_distinct_topics(set_id)

    return render_template(
        'flashcards.html',
        active_page='library',
        study_set=study_set,
        cards=cards,
        topics=topics
    )

@app.route('/study/<int:set_id>/quiz')
def take_quiz(set_id):
    study_set = get_study_set(set_id)
    if not study_set:
        return redirect(url_for('dashboard'))

    questions = get_quiz_questions(set_id)

    return render_template(
        'quiz.html',
        active_page='library',
        study_set=study_set,
        questions=questions
    )

@app.route('/study/<int:set_id>/export-pdf')
def export_pdf(set_id):
    study_set = get_study_set(set_id)
    if not study_set:
        return redirect(url_for('dashboard'))

    cards = get_flashcards(set_id)
    questions = get_quiz_questions(set_id)

    pdf_path = export_study_set_to_pdf(study_set, cards, questions)
    return send_file(
        pdf_path,
        as_attachment=True,
        download_name=os.path.basename(pdf_path),
        mimetype='application/pdf'
    )

@app.route('/library')
def library():
    all_sets = get_all_study_sets()
    return render_template('library.html', active_page='library', sets=all_sets)

@app.route('/performance')
def performance():
    perf_data = get_performance_data()
    return render_template(
        'performance.html',
        active_page='performance',
        **perf_data
    )

# ==================== API Endpoints ====================

@app.route('/api/generate', methods=['POST'])
def api_generate():
    try:
        notes = request.form.get('notes', '').strip()
        difficulty = request.form.get('difficulty', 'Medium')
        topic_focus = request.form.get('topic_focus', '').strip()
        question_count = int(request.form.get('question_count', 10))
        model_name = request.form.get('model_name', '').strip() or None

        create_flashcards = bool(request.form.get('create_flashcards'))
        create_quiz = bool(request.form.get('create_quiz'))
        create_summary = bool(request.form.get('create_summary'))

        extracted_text = ""
        source_type = "Pasted notes"
        original_filename = None

        # Check if file was uploaded
        if 'file' in request.files and request.files['file'].filename:
            file = request.files['file']
            filename = secure_filename(file.filename)
            ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
            
            if ext in app.config['ALLOWED_EXTENSIONS']:
                original_filename = filename
                saved_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(saved_path)

                if ext == 'pdf':
                    source_type = "PDF"
                    extracted_text = extract_text_from_pdf(saved_path)
                elif ext == 'txt':
                    source_type = "TXT"
                    extracted_text = extract_text_from_txt(saved_path)
            else:
                return jsonify({'success': False, 'error': 'Invalid file format. Please upload PDF or TXT.'}), 400

        # Combine or fallback to pasted notes
        if notes:
            if extracted_text:
                extracted_text += "\n\n" + notes
            else:
                extracted_text = notes
                if not original_filename:
                    source_type = "Pasted notes"

        if not extracted_text.strip():
            return jsonify({'success': False, 'error': 'Could not extract any readable text from your upload. Please check your document or paste notes.'}), 400

        # Run AI generation with selected model
        result = generate_study_material(
            raw_text=extracted_text,
            create_flashcards=create_flashcards,
            create_quiz=create_quiz,
            create_summary=create_summary,
            difficulty=difficulty,
            topic_focus=topic_focus,
            question_count=question_count,
            model_name=model_name
        )

        title = result.get('title') or "Untitled Study Set"
        summary = result.get('summary') or ""
        flashcards = result.get('flashcards') or []
        quiz_questions = result.get('quiz') or []

        # Save to database
        set_id = create_study_set(
            title=title,
            source_type=source_type,
            original_filename=original_filename,
            raw_text=extracted_text[:10000],
            summary=summary,
            difficulty=difficulty,
            topic_focus=topic_focus
        )

        if create_flashcards and flashcards:
            add_flashcards(set_id, flashcards)

        if create_quiz and quiz_questions:
            add_quiz_questions(set_id, quiz_questions, difficulty=difficulty)

        engine_msg = "Llama-3 (Groq AI)" if result.get('generator_type') == 'groq' else "Local NLP Generator"
        
        return jsonify({
            'success': True,
            'study_set_id': set_id,
            'message': f"Study set generated successfully with {engine_msg}!",
            'has_flashcards': bool(flashcards),
            'has_quiz': bool(quiz_questions),
            'generator_type': result.get('generator_type')
        })

    except Exception as e:
        print(f"Error in api_generate: {e}")
        return jsonify({'success': False, 'error': f"Generation failed: {str(e)}"}), 500

@app.route('/api/quiz/<int:set_id>/submit', methods=['POST'])
def api_quiz_submit(set_id):
    try:
        data = request.get_json() or {}
        user_answers = data.get('answers', {})
        
        questions = get_quiz_questions(set_id)
        if not questions:
            return jsonify({'success': False, 'error': 'No questions found for this quiz.'}), 404

        total = len(questions)
        correct_count = 0
        detailed_eval = []

        for idx, q in enumerate(questions):
            # User choice could be string or int key in json
            chosen = user_answers.get(str(idx), user_answers.get(idx))
            is_correct = (chosen is not None and int(chosen) == q['correct_index'])
            if is_correct:
                correct_count += 1

            detailed_eval.append({
                'question_index': idx,
                'chosen': chosen,
                'correct_index': q['correct_index'],
                'is_correct': is_correct,
                'explanation': q.get('explanation', '')
            })

        score_percentage = round((correct_count / total) * 100) if total > 0 else 0

        # Save attempt to database
        attempt_id = save_quiz_attempt(
            set_id=set_id,
            score_percentage=score_percentage,
            correct_count=correct_count,
            total_questions=total,
            answers_json=user_answers
        )

        return jsonify({
            'success': True,
            'attempt_id': attempt_id,
            'score_percentage': score_percentage,
            'correct_count': correct_count,
            'total_questions': total,
            'evaluations': detailed_eval
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/study-set/<int:set_id>/delete', methods=['POST'])
def api_delete_set(set_id):
    delete_study_set(set_id)
    return jsonify({'success': True})

@app.route('/api/card/<int:card_id>/status', methods=['POST'])
def api_card_status(card_id):
    data = request.get_json() or {}
    status = data.get('status', 'new')
    update_card_status(card_id, status)
    return jsonify({'success': True})

@app.route('/api/settings/groq-key', methods=['GET', 'POST'])
def api_settings_groq_key():
    if request.method == 'POST':
        data = request.get_json() or {}
        key = data.get('key', '').strip()
        model = data.get('model', 'openai/gpt-oss-120b').strip()
        if key:
            set_app_setting('groq_api_key', key)
        if model:
            set_app_setting('groq_model', model)
        
        # Also update .env
        try:
            env_file = os.path.join(Config.BASE_DIR, '.env')
            lines = []
            if os.path.exists(env_file):
                with open(env_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
            
            key_set = False
            model_set = False
            new_lines = []
            for line in lines:
                if line.startswith('GROQ_API_KEY='):
                    new_lines.append(f"GROQ_API_KEY={key}\n")
                    key_set = True
                elif line.startswith('GROQ_MODEL='):
                    new_lines.append(f"GROQ_MODEL={model}\n")
                    model_set = True
                else:
                    new_lines.append(line)
            if not key_set and key:
                new_lines.append(f"GROQ_API_KEY={key}\n")
            if not model_set and model:
                new_lines.append(f"GROQ_MODEL={model}\n")
            with open(env_file, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
        except Exception:
            pass

        return jsonify({'success': True, 'is_set': bool(key), 'model': model})
    else:
        active_key = get_active_groq_api_key()
        active_model = get_active_groq_model()
        preview = f"{active_key[:6]}...{active_key[-4:]}" if len(active_key) > 10 else ("Configured" if active_key else "None")
        return jsonify({
            'key': active_key,
            'is_set': bool(active_key),
            'preview': preview,
            'model': active_model
        })

def find_available_port(start_port=5000, max_attempts=10):
    import socket
    for p in range(start_port, start_port + max_attempts):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(('127.0.0.1', p))
            s.close()
            return p
        except OSError:
            continue
    return start_port

if __name__ == '__main__':
    import webbrowser
    import threading

    is_cloud = 'PORT' in os.environ or 'RENDER' in os.environ
    requested_port = int(os.environ.get('PORT', 5000))
    port = requested_port if is_cloud else find_available_port(requested_port)
    host = os.environ.get('HOST', '0.0.0.0' if is_cloud else '127.0.0.1')
    url = f"http://{'localhost' if host == '0.0.0.0' else host}:{port}"

    print("\n" + "=" * 58)
    print("[*] NoteSpark is running successfully!")
    print(f"[>] Open in browser: {url}")
    print("=" * 58 + "\n")

    # Optionally auto-open browser in a background timer (only on local machines)
    if not is_cloud and os.environ.get('OPEN_BROWSER', '1') == '1':
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()

    app.run(host=host, port=port, debug=False)
