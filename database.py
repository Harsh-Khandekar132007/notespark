import sqlite3
import json
import os
from config import Config

def get_db_connection():
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Study Sets table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS study_sets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        source_type TEXT NOT NULL DEFAULT 'Pasted notes',
        original_filename TEXT,
        raw_text TEXT,
        summary TEXT,
        difficulty TEXT DEFAULT 'Medium',
        topic_focus TEXT,
        card_count INTEGER DEFAULT 0,
        question_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Flashcards table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS flashcards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        study_set_id INTEGER NOT NULL,
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        topic TEXT DEFAULT 'General',
        card_order INTEGER DEFAULT 0,
        status TEXT DEFAULT 'new',
        FOREIGN KEY (study_set_id) REFERENCES study_sets (id) ON DELETE CASCADE
    )
    ''')
    
    # Quiz questions table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS quiz_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        study_set_id INTEGER NOT NULL,
        question TEXT NOT NULL,
        options TEXT NOT NULL, -- JSON array of 4 strings
        correct_index INTEGER NOT NULL,
        explanation TEXT,
        topic TEXT DEFAULT 'General',
        difficulty TEXT DEFAULT 'Medium',
        question_order INTEGER DEFAULT 0,
        FOREIGN KEY (study_set_id) REFERENCES study_sets (id) ON DELETE CASCADE
    )
    ''')
    
    # Quiz attempts / performance table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS quiz_attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        study_set_id INTEGER NOT NULL,
        score_percentage INTEGER NOT NULL,
        correct_count INTEGER NOT NULL,
        total_questions INTEGER NOT NULL,
        answers_json TEXT, -- JSON recording user choices
        completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (study_set_id) REFERENCES study_sets (id) ON DELETE CASCADE
    )
    ''')

    # App settings table (for persisting user Groq API Key or preferences)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS app_settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    ''')
    
    conn.commit()
    conn.close()
    
    # Seed sample sets if table is empty
    seed_default_data()

def seed_default_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) as count FROM study_sets')
    row = cursor.fetchone()
    if row['count'] == 0:
        # 1. Operating Systems: Process Scheduling
        cursor.execute('''
        INSERT INTO study_sets (title, source_type, original_filename, raw_text, summary, difficulty, topic_focus, card_count, question_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            "Operating Systems: Process Scheduling",
            "PDF",
            "operating_systems_scheduling.pdf",
            "CPU scheduling is the basis of multi-programmed operating systems. By switching the CPU among processes, the operating system can make the computer more productive. The objective of multiprogramming is to have some process running at all times, to maximize CPU utilization. Process scheduling algorithms decide which ready process runs next.",
            "CPU scheduling decides which ready process runs next. Algorithms trade throughput, waiting time, turnaround time, and fairness. First-Come-First-Served (FCFS) is non-preemptive with potential convoy effect. Shortest Job First (SJF) minimizes average waiting time but risks starvation for longer tasks. Round Robin (RR) allocates a fixed time quantum for interactive responsiveness.",
            "Medium",
            "Process scheduling",
            24,
            10
        ))
        os_set_id = cursor.lastrowid
        
        # Flashcards for OS
        os_cards = [
            ("Which scheduling algorithm assigns the CPU to the process with the smallest next burst?", "Shortest Job First (SJF)", "SJF", 1),
            ("What is the primary drawback of First-Come, First-Served (FCFS) scheduling?", "The convoy effect, where short processes wait behind long CPU-bound processes, leading to high average waiting time.", "FCFS", 2),
            ("What scheduling algorithm is designed specifically for time-sharing systems?", "Round Robin (RR) scheduling, which allocates a small unit of CPU time (time quantum) to each process in turn.", "Round Robin", 3),
            ("Which scheduling algorithm can cause starvation of long processes?", "Shortest Job First (SJF) and Priority Scheduling, because a steady stream of shorter or higher-priority processes can delay long processes indefinitely.", "SJF", 4),
            ("What is a time quantum (or time slice)?", "A small unit of CPU time (typically 10 to 100 milliseconds) allocated to a process in Round Robin scheduling before preemption.", "Round Robin", 5),
            ("Define turnaround time in CPU scheduling.", "The interval from the time of submission of a process to the time of its completion.", "General", 6),
            ("What is the difference between preemptive and non-preemptive scheduling?", "In non-preemptive scheduling, once the CPU has been allocated to a process, the process keeps it until it releases it either by terminating or by switching to waiting. Preemptive scheduling allows the OS to interrupt a running process.", "General", 7),
            ("What is Multilevel Feedback Queue scheduling?", "A scheduling algorithm that allows a process to move between queues based on its CPU burst characteristics and aging.", "General", 8)
        ]
        
        for q, a, top, ord_idx in os_cards:
            cursor.execute('''
            INSERT INTO flashcards (study_set_id, question, answer, topic, card_order)
            VALUES (?, ?, ?, ?, ?)
            ''', (os_set_id, q, a, top, ord_idx))
            
        # OS Quiz Questions
        os_questions = [
            (
                "Which scheduling algorithm assigns the CPU to the process with the smallest next burst?",
                ["First Come First Served", "Shortest Job First", "Round Robin", "Multilevel feedback queue"],
                1,
                "Shortest Job First (SJF) selects the process with the minimum CPU burst time, achieving the lowest average waiting time.",
                "SJF", "Medium", 1
            ),
            (
                "What is the convoy effect in operating systems?",
                ["When short processes block all I/O devices", "When many short processes wait for one long CPU-bound process to release the CPU", "When multiple processes enter a deadlock state", "When the OS runs out of ready queues"],
                1,
                "In FCFS scheduling, when one long process holds the CPU, all subsequent shorter processes are forced to wait, creating a convoy effect.",
                "FCFS", "Easy", 2
            ),
            (
                "In Round Robin scheduling, what happens if the time quantum is extremely large?",
                ["It becomes identical to First-Come, First-Served (FCFS)", "Context switching overhead becomes unacceptable", "Starvation increases exponentially", "Throughput drops to zero"],
                0,
                "If the time quantum is greater than the longest CPU burst, Round Robin degenerates into FCFS scheduling.",
                "Round Robin", "Medium", 3
            ),
            (
                "Which scheduling metric represents the time elapsed from submission to completion?",
                ["Waiting time", "Response time", "Turnaround time", "Throughput"],
                2,
                "Turnaround time is the total sum of periods spent waiting in the ready queue, executing on the CPU, and doing I/O.",
                "General", "Easy", 4
            ),
            (
                "Which scheduling algorithm can cause starvation of long processes?",
                ["First Come First Served", "Shortest Job First", "Round Robin", "Multilevel feedback queue"],
                1,
                "SJF can starve long jobs if new shorter jobs keep arriving continuously.",
                "Process scheduling", "Medium", 5
            ),
            (
                "What technique is commonly used to prevent starvation in priority scheduling?",
                ["Aging", "Compaction", "Paging", "Thrashing"],
                0,
                "Aging gradually increases the priority of processes that wait in the system for a long time.",
                "General", "Medium", 6
            ),
            (
                "In preemptive scheduling, a process can be moved from running to ready when:",
                ["An I/O operation completes", "An interrupt or timer expiration occurs", "The process explicitly calls exit()", "The process waits for a mutex"],
                1,
                "Preemption occurs when a timer interrupt signals the end of a time slice or a higher-priority task arrives.",
                "General", "Hard", 7
            ),
            (
                "Which scheduling algorithm is optimal in terms of minimizing average waiting time?",
                ["FCFS", "Priority Scheduling", "Shortest Job First", "Round Robin"],
                2,
                "Shortest Job First is provably optimal for minimizing the average waiting time for a given set of processes.",
                "SJF", "Medium", 8
            ),
            (
                "What is the role of the dispatcher in an operating system?",
                ["Deciding which process to schedule next", "Giving control of the CPU to the process selected by the short-term scheduler", "Allocating RAM to incoming processes", "Managing filesystem caches"],
                1,
                "The dispatcher switches context, switches to user mode, and jumps to the proper location in the user program to restart that program.",
                "General", "Hard", 9
            ),
            (
                "Which of the following is true regarding Multilevel Feedback Queue (MLFQ)?",
                ["Processes cannot move between queues", "It requires all jobs to have identical burst times", "It dynamically adjusts process priority based on observed behavior", "It only supports non-preemptive execution"],
                2,
                "MLFQ separates processes with different CPU burst characteristics and moves I/O-bound jobs to higher-priority queues.",
                "General", "Hard", 10
            )
        ]
        
        for q, opts, c_idx, expl, top, diff, q_ord in os_questions:
            cursor.execute('''
            INSERT INTO quiz_questions (study_set_id, question, options, correct_index, explanation, topic, difficulty, question_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (os_set_id, q, json.dumps(opts), c_idx, expl, top, diff, q_ord))

        # 2. Organic Chemistry: Reactions
        cursor.execute('''
        INSERT INTO study_sets (title, source_type, original_filename, raw_text, summary, difficulty, topic_focus, card_count, question_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            "Organic Chemistry: Reactions",
            "Pasted notes",
            None,
            "Nucleophilic substitution reactions (SN1 and SN2) differ by mechanism, kinetics, stereochemistry, and solvent effects. Electrophilic additions in alkenes follow Markovnikov rule.",
            "Covers SN1 vs SN2 mechanisms, E1 vs E2 eliminations, Markovnikov addition to alkenes, and carbonyl chemistry. SN2 proceeds via concerted backside attack with stereochemical inversion, favored by polar aprotic solvents and primary substrates.",
            "Hard",
            "Substitution & Elimination",
            30,
            15
        ))
        chem_set_id = cursor.lastrowid
        cursor.execute('''
        INSERT INTO flashcards (study_set_id, question, answer, topic, card_order)
        VALUES (?, ?, ?, ?, ?)
        ''', (chem_set_id, "What stereochemical outcome occurs in an SN2 reaction?", "Complete inversion of configuration (Walden inversion) due to backside nucleophilic attack.", "SN2", 1))
        cursor.execute('''
        INSERT INTO quiz_questions (study_set_id, question, options, correct_index, explanation, topic, difficulty, question_order)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (chem_set_id, "Which solvent is most favorable for an SN2 reaction?", json.dumps(["Water (polar protic)", "Ethanol (polar protic)", "Acetone (polar aprotic)", "Hexane (nonpolar)"]), 2, "Polar aprotic solvents like acetone or DMSO solvate cations but leave nucleophiles naked and reactive.", "SN2", "Medium", 1))

        # 3. Data Structures: Trees
        cursor.execute('''
        INSERT INTO study_sets (title, source_type, original_filename, raw_text, summary, difficulty, topic_focus, card_count, question_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            "Data Structures: Trees",
            "TXT",
            "trees_lecture.txt",
            "Binary Search Trees (BST), AVL Trees, Red-Black Trees, and B-Trees. Tree traversal algorithms: In-order, Pre-order, Post-order, Level-order.",
            "Analysis of binary trees, balanced search trees (AVL and Red-Black), and multi-way search trees (B-Trees). Covers search, insert, and delete operations with time complexities.",
            "Medium",
            "Balanced Trees",
            18,
            10
        ))
        tree_set_id = cursor.lastrowid
        cursor.execute('''
        INSERT INTO flashcards (study_set_id, question, answer, topic, card_order)
        VALUES (?, ?, ?, ?, ?)
        ''', (tree_set_id, "What traversal of a Binary Search Tree produces keys in ascending sorted order?", "In-order traversal (Left, Root, Right).", "Traversal", 1))
        cursor.execute('''
        INSERT INTO quiz_questions (study_set_id, question, options, correct_index, explanation, topic, difficulty, question_order)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (tree_set_id, "What is the worst-case time complexity of searching a degenerate (unbalanced) BST?", json.dumps(["O(1)", "O(log n)", "O(n)", "O(n log n)"]), 2, "An unbalanced BST degenerates into a linked list, requiring linear O(n) search time.", "BST", "Easy", 1))

        # 4. Microeconomics: Demand and Supply
        cursor.execute('''
        INSERT INTO study_sets (title, source_type, original_filename, raw_text, summary, difficulty, topic_focus, card_count, question_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            "Microeconomics: Demand and Supply",
            "PDF",
            "microeconomics_ch3.pdf",
            "The law of demand states price and quantity demanded are inversely related. Market equilibrium occurs where quantity supplied equals quantity demanded.",
            "Fundamental principles of price determination, price elasticity of demand and supply, consumer surplus, producer surplus, and deadweight loss from price controls.",
            "Easy",
            "Equilibrium & Elasticity",
            20,
            10
        ))
        econ_set_id = cursor.lastrowid
        cursor.execute('''
        INSERT INTO flashcards (study_set_id, question, answer, topic, card_order)
        VALUES (?, ?, ?, ?, ?)
        ''', (econ_set_id, "What happens to consumer surplus when market price falls?", "Consumer surplus increases as existing buyers pay less and new buyers enter the market.", "Equilibrium", 1))
        cursor.execute('''
        INSERT INTO quiz_questions (study_set_id, question, options, correct_index, explanation, topic, difficulty, question_order)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (econ_set_id, "If cross-price elasticity of demand between two goods is positive, the goods are:", json.dumps(["Complements", "Substitutes", "Normal goods", "Inferior goods"]), 1, "Positive cross-price elasticity means an increase in the price of Good A raises demand for Good B (substitutes).", "Elasticity", "Easy", 1))

        # Real tests only: No dummy quiz attempts seeded
        conn.commit()

    conn.close()

def get_all_study_sets():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM study_sets ORDER BY created_at DESC')
    sets = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return sets

def get_study_set(set_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM study_sets WHERE id = ?', (set_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_flashcards(set_id, topic=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if topic and topic.lower() != 'all':
        cursor.execute('SELECT * FROM flashcards WHERE study_set_id = ? AND LOWER(topic) = LOWER(?) ORDER BY card_order ASC, id ASC', (set_id, topic))
    else:
        cursor.execute('SELECT * FROM flashcards WHERE study_set_id = ? ORDER BY card_order ASC, id ASC', (set_id,))
    cards = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return cards

def get_distinct_topics(set_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT topic FROM flashcards WHERE study_set_id = ? AND topic IS NOT NULL AND topic != ""', (set_id,))
    topics = [row['topic'] for row in cursor.fetchall()]
    conn.close()
    return topics

def get_quiz_questions(set_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM quiz_questions WHERE study_set_id = ? ORDER BY question_order ASC, id ASC', (set_id,))
    rows = cursor.fetchall()
    questions = []
    for row in rows:
        d = dict(row)
        try:
            d['options'] = json.loads(d['options'])
        except Exception:
            d['options'] = ["Option A", "Option B", "Option C", "Option D"]
        questions.append(d)
    conn.close()
    return questions

def create_study_set(title, source_type, original_filename, raw_text, summary, difficulty, topic_focus, card_count=0, question_count=0):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO study_sets (title, source_type, original_filename, raw_text, summary, difficulty, topic_focus, card_count, question_count)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (title, source_type, original_filename, raw_text, summary, difficulty, topic_focus, card_count, question_count))
    set_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return set_id

def add_flashcards(set_id, flashcards_list):
    conn = get_db_connection()
    cursor = conn.cursor()
    for idx, card in enumerate(flashcards_list, start=1):
        q = card.get('question', '').strip()
        a = card.get('answer', '').strip()
        top = card.get('topic', 'General').strip()
        if q and a:
            cursor.execute('''
            INSERT INTO flashcards (study_set_id, question, answer, topic, card_order)
            VALUES (?, ?, ?, ?, ?)
            ''', (set_id, q, a, top, idx))
    
    # update card count in study_sets
    cursor.execute('UPDATE study_sets SET card_count = (SELECT COUNT(*) FROM flashcards WHERE study_set_id = ?) WHERE id = ?', (set_id, set_id))
    conn.commit()
    conn.close()

def add_quiz_questions(set_id, questions_list, difficulty='Medium'):
    conn = get_db_connection()
    cursor = conn.cursor()
    for idx, q_item in enumerate(questions_list, start=1):
        q = q_item.get('question', '').strip()
        opts = q_item.get('options', [])
        c_idx = q_item.get('correct_index', 0)
        expl = q_item.get('explanation', '')
        top = q_item.get('topic', 'General')
        diff = q_item.get('difficulty', difficulty)
        if q and len(opts) >= 2:
            cursor.execute('''
            INSERT INTO quiz_questions (study_set_id, question, options, correct_index, explanation, topic, difficulty, question_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (set_id, q, json.dumps(opts), c_idx, expl, top, diff, idx))
            
    # update question count in study_sets
    cursor.execute('UPDATE study_sets SET question_count = (SELECT COUNT(*) FROM quiz_questions WHERE study_set_id = ?) WHERE id = ?', (set_id, set_id))
    conn.commit()
    conn.close()

def save_quiz_attempt(set_id, score_percentage, correct_count, total_questions, answers_json):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO quiz_attempts (study_set_id, score_percentage, correct_count, total_questions, answers_json)
    VALUES (?, ?, ?, ?, ?)
    ''', (set_id, score_percentage, correct_count, total_questions, json.dumps(answers_json)))
    attempt_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return attempt_id

def get_recent_attempts(limit=6):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT qa.*, ss.title as set_title
    FROM quiz_attempts qa
    JOIN study_sets ss ON qa.study_set_id = ss.id
    ORDER BY qa.completed_at DESC, qa.id DESC
    LIMIT ?
    ''', (limit,))
    attempts = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return list(reversed(attempts))

def get_overall_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) as count FROM study_sets')
    total_sets = cursor.fetchone()['count']
    
    cursor.execute('SELECT COUNT(*) as count, AVG(score_percentage) as avg_score, MAX(score_percentage) as max_score FROM quiz_attempts')
    row = cursor.fetchone()
    total_quizzes = row['count']
    avg_score = round(row['avg_score'] or 0)
    highest_score = row['max_score'] or 0
    
    cursor.execute('SELECT COUNT(*) as count FROM flashcards')
    total_cards = cursor.fetchone()['count']

    conn.close()
    return {
        'total_sets': total_sets,
        'total_quizzes': total_quizzes,
        'avg_score': avg_score,
        'highest_score': highest_score,
        'total_cards': total_cards
    }

def get_performance_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT qa.*, ss.title as set_title, ss.difficulty as set_difficulty, ss.topic_focus as set_topic
        FROM quiz_attempts qa
        JOIN study_sets ss ON qa.study_set_id = ss.id
        ORDER BY qa.completed_at DESC, qa.id DESC
    ''')
    all_attempts = [dict(r) for r in cursor.fetchall()]
    
    total_quizzes = len(all_attempts)
    avg_score = round(sum(a['score_percentage'] for a in all_attempts) / total_quizzes) if total_quizzes > 0 else 0
    highest_score = max((a['score_percentage'] for a in all_attempts), default=0)
    
    latest_attempt = None
    latest_breakdown = None
    
    if all_attempts:
        latest = all_attempts[0]
        latest_attempt = latest
        
        # Deep inspection of the latest test attempt
        set_id = latest['study_set_id']
        cursor.execute('''
            SELECT * FROM quiz_questions WHERE study_set_id = ? ORDER BY question_order ASC, id ASC
        ''', (set_id,))
        q_rows = cursor.fetchall()
        
        try:
            user_ans = json.loads(latest.get('answers_json') or '{}')
        except Exception:
            user_ans = {}
            
        topics_stat = {}
        incorrect_questions = []
        
        for idx, q_row in enumerate(q_rows):
            q_dict = dict(q_row)
            top = q_dict.get('topic') or 'General'
            if top not in topics_stat:
                topics_stat[top] = {'correct': 0, 'total': 0}
            topics_stat[top]['total'] += 1
            
            chosen = user_ans.get(str(idx), user_ans.get(idx))
            c_idx = q_dict.get('correct_index', 0)
            is_corr = (chosen is not None and int(chosen) == c_idx)
            
            if is_corr:
                topics_stat[top]['correct'] += 1
            else:
                opts = []
                try:
                    opts = json.loads(q_dict.get('options') or '[]')
                except Exception:
                    pass
                chosen_text = opts[int(chosen)] if (chosen is not None and int(chosen) < len(opts)) else "Unanswered"
                correct_text = opts[c_idx] if c_idx < len(opts) else ""
                incorrect_questions.append({
                    'index': idx + 1,
                    'question': q_dict.get('question'),
                    'topic': top,
                    'chosen': chosen_text,
                    'correct': correct_text,
                    'explanation': q_dict.get('explanation') or ''
                })
                
        topic_summary = []
        for t_name, t_data in topics_stat.items():
            pct = round((t_data['correct'] / t_data['total']) * 100) if t_data['total'] > 0 else 0
            topic_summary.append({
                'topic': t_name,
                'correct': t_data['correct'],
                'total': t_data['total'],
                'pct': pct
            })
            
        latest_breakdown = {
            'set_title': latest['set_title'],
            'study_set_id': latest['study_set_id'],
            'score_percentage': latest['score_percentage'],
            'correct_count': latest['correct_count'],
            'total_questions': latest['total_questions'],
            'completed_at': latest['completed_at'],
            'topics': topic_summary,
            'incorrect_questions': incorrect_questions
        }

    # Chart attempts (up to 8 most recent attempts, ordered chronologically)
    recent_chronological = list(reversed(all_attempts[:8]))
    chart_attempts = []
    for idx, att in enumerate(recent_chronological, start=1):
        pct = att['score_percentage']
        color = '#10B981' if pct >= 80 else ('#F59E0B' if pct >= 60 else '#EF4444')
        chart_attempts.append({
            'label': f"Test {idx}",
            'pct': pct,
            'title': att['set_title'],
            'color': color,
            'date': att['completed_at'][:10],
            'correct': att['correct_count'],
            'total': att['total_questions']
        })

    # Available sets for quick taking
    cursor.execute('''
        SELECT id, title, question_count, difficulty
        FROM study_sets
        WHERE question_count > 0
        ORDER BY created_at DESC
        LIMIT 6
    ''', ())
    available_quiz_sets = [dict(r) for r in cursor.fetchall()]

    conn.close()
    
    return {
        'total_quizzes': total_quizzes,
        'avg_score': avg_score,
        'highest_score': highest_score,
        'latest_attempt': latest_attempt,
        'latest_breakdown': latest_breakdown,
        'chart_attempts': chart_attempts,
        'all_attempts': all_attempts,
        'available_quiz_sets': available_quiz_sets
    }

def delete_study_set(set_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM flashcards WHERE study_set_id = ?', (set_id,))
    cursor.execute('DELETE FROM quiz_questions WHERE study_set_id = ?', (set_id,))
    cursor.execute('DELETE FROM quiz_attempts WHERE study_set_id = ?', (set_id,))
    cursor.execute('DELETE FROM study_sets WHERE id = ?', (set_id,))
    conn.commit()
    conn.close()

def update_card_status(card_id, status):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE flashcards SET status = ? WHERE id = ?', (status, card_id))
    conn.commit()
    conn.close()

def get_app_setting(key, default=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM app_settings WHERE key = ?', (key,))
    row = cursor.fetchone()
    conn.close()
    return row['value'] if row else default

def set_app_setting(key, value):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO app_settings (key, value) VALUES (?, ?)
    ON CONFLICT(key) DO UPDATE SET value = excluded.value
    ''', (key, value))
    conn.commit()
    conn.close()
