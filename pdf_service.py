import os
import re
from datetime import datetime
from config import Config

# ReportLab for PDF export
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)

def extract_text_from_pdf(file_path):
    """
    Extracts text from a PDF file using PyPDF2 with PyMuPDF (fitz) fallback.
    """
    text = ""
    # Try PyPDF2 first (requirement)
    try:
        import PyPDF2
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"PyPDF2 extraction notice: {e}")

    # If PyPDF2 extracted little or no text, try PyMuPDF (fitz)
    if len(text.strip()) < 50:
        try:
            import fitz
            doc = fitz.open(file_path)
            fitz_text = ""
            for page in doc:
                fitz_text += page.get_text() + "\n"
            if len(fitz_text.strip()) > len(text.strip()):
                text = fitz_text
        except Exception as e:
            print(f"PyMuPDF fallback notice: {e}")

    return clean_extracted_text(text)

def extract_text_from_txt(file_path):
    """Extracts text from a plain text file."""
    for enc in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
        try:
            with open(file_path, "r", encoding=enc) as f:
                return clean_extracted_text(f.read())
        except UnicodeDecodeError:
            continue
    with open(file_path, "r", errors="ignore") as f:
        return clean_extracted_text(f.read())

def clean_extracted_text(text):
    """Cleans up text, strips excess whitespace, and normalizes line breaks."""
    if not text:
        return ""
    # Replace carriage returns
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Remove null bytes
    text = text.replace('\x00', '')
    return text.strip()

def export_study_set_to_pdf(study_set, flashcards, quiz_questions):
    """
    Generates a PDF document for a study set including:
    1. Study Set Header and Metadata
    2. AI Notes Summary
    3. Flashcards Collection (Question & Answer)
    4. Multiple Choice Quiz Questions
    5. Answer Key with Explanations
    """
    os.makedirs(Config.EXPORT_FOLDER, exist_ok=True)
    safe_title = re.sub(r'[^a-zA-Z0-9_\- ]', '', study_set.get('title', 'study_set')).replace(' ', '_')
    filename = f"{safe_title}_{study_set['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    file_path = os.path.join(Config.EXPORT_FOLDER, filename)

    doc = SimpleDocTemplate(
        file_path,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    # Custom styles
    primary_color = colors.HexColor("#4338CA")
    dark_text = colors.HexColor("#141A2E")
    muted_text = colors.HexColor("#55607A")
    border_color = colors.HexColor("#DDE1EC")
    bg_light = colors.HexColor("#F8F9FD")
    card_bg = colors.HexColor("#FFFFFF")
    badge_bg = colors.HexColor("#E7E8FB")

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=dark_text,
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=14,
        textColor=muted_text,
        spaceAfter=15
    )

    h2_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=primary_color,
        spaceBefore=14,
        spaceAfter=8
    )

    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=dark_text
    )

    summary_style = ParagraphStyle(
        'SummaryText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=15,
        textColor=dark_text
    )

    bold_label = ParagraphStyle(
        'BoldLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=dark_text
    )

    answer_style = ParagraphStyle(
        'AnswerText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#0F766E")
    )

    story = []

    # Brand Header
    header_data = [
        [
            Paragraph("<b>NoteSpark</b> · Smart Study Guide", ParagraphStyle('Brd', fontName='Helvetica-Bold', fontSize=10, textColor=primary_color)),
            Paragraph(datetime.now().strftime("%B %d, %Y"), ParagraphStyle('Dt', fontName='Helvetica', fontSize=9, textColor=muted_text, alignment=2))
        ]
    ]
    t_header = Table(header_data, colWidths=[350, 180])
    t_header.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_header)
    story.append(HRFlowable(width="100%", thickness=1, color=border_color, spaceBefore=4, spaceAfter=14))

    # Title & Metadata
    story.append(Paragraph(study_set.get('title', 'Study Set'), title_style))
    meta_info = f"Source: {study_set.get('source_type', 'Notes')} | Difficulty: {study_set.get('difficulty', 'Medium')} | {len(flashcards)} Flashcards | {len(quiz_questions)} Questions"
    story.append(Paragraph(meta_info, subtitle_style))

    # 1. Notes Summary Section
    if study_set.get('summary'):
        story.append(Paragraph("AI Notes Summary", h2_style))
        summary_box = [
            [Paragraph(study_set['summary'], summary_style)]
        ]
        t_summary = Table(summary_box, colWidths=[530])
        t_summary.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), bg_light),
            ('BOX', (0, 0), (-1, -1), 1, border_color),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ]))
        story.append(t_summary)
        story.append(Spacer(1, 14))

    # 2. Flashcards Section
    if flashcards:
        story.append(Paragraph(f"Flashcards ({len(flashcards)} cards)", h2_style))
        card_table_data = [
            [
                Paragraph("<b>#</b>", bold_label),
                Paragraph("<b>Topic</b>", bold_label),
                Paragraph("<b>Question / Term</b>", bold_label),
                Paragraph("<b>Answer / Explanation</b>", bold_label)
            ]
        ]
        for idx, card in enumerate(flashcards, start=1):
            q_p = Paragraph(card['question'], body_style)
            a_p = Paragraph(card['answer'], answer_style)
            top_p = Paragraph(f"<i>{card.get('topic', 'General')}</i>", ParagraphStyle('Tp', fontName='Helvetica-Oblique', fontSize=8.5, textColor=muted_text))
            card_table_data.append([str(idx), top_p, q_p, a_p])

        t_cards = Table(card_table_data, colWidths=[24, 76, 215, 215])
        t_cards.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), badge_bg),
            ('TEXTCOLOR', (0, 0), (-1, 0), primary_color),
            ('GRID', (0, 0), (-1, -1), 0.5, border_color),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, bg_light]),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(t_cards)
        story.append(Spacer(1, 16))

    # 3. Quiz Section
    if quiz_questions:
        story.append(PageBreak())
        story.append(Paragraph(f"Multiple-Choice Quiz ({len(quiz_questions)} Questions)", h2_style))
        story.append(Paragraph("Choose the best answer for each question. Answers and explanations are provided on the final page.", subtitle_style))

        opt_labels = ["A", "B", "C", "D", "E"]
        for idx, q_item in enumerate(quiz_questions, start=1):
            q_flow = []
            topic_str = f" [{q_item.get('topic', 'General')} · {q_item.get('difficulty', 'Medium')}]"
            q_text = f"<b>{idx}. {q_item['question']}</b> <font color='#55607A' size='8'>{topic_str}</font>"
            q_flow.append(Paragraph(q_text, body_style))
            q_flow.append(Spacer(1, 4))

            options = q_item.get('options', [])
            for opt_idx, opt in enumerate(options):
                lbl = opt_labels[opt_idx] if opt_idx < len(opt_labels) else str(opt_idx + 1)
                opt_text = f"&nbsp;&nbsp;<b>({lbl})</b> {opt}"
                q_flow.append(Paragraph(opt_text, body_style))
                q_flow.append(Spacer(1, 2))

            q_flow.append(Spacer(1, 6))
            story.append(KeepTogether(q_flow))

        # 4. Answer Key Section
        story.append(Spacer(1, 10))
        story.append(Paragraph("Quiz Answer Key & Explanations", h2_style))
        ans_rows = [
            [
                Paragraph("<b>Q#</b>", bold_label),
                Paragraph("<b>Correct Option</b>", bold_label),
                Paragraph("<b>Explanation</b>", bold_label)
            ]
        ]
        for idx, q_item in enumerate(quiz_questions, start=1):
            c_idx = q_item.get('correct_index', 0)
            options = q_item.get('options', [])
            c_label = opt_labels[c_idx] if c_idx < len(opt_labels) else str(c_idx + 1)
            c_text = options[c_idx] if c_idx < len(options) else f"Option {c_label}"
            ans_p = Paragraph(f"<b>({c_label})</b> {c_text}", answer_style)
            expl_p = Paragraph(q_item.get('explanation', 'No explanation provided.'), body_style)
            ans_rows.append([str(idx), ans_p, expl_p])

        t_ans = Table(ans_rows, colWidths=[30, 180, 320])
        t_ans.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), badge_bg),
            ('GRID', (0, 0), (-1, -1), 0.5, border_color),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, bg_light]),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(t_ans)

    # Build document
    doc.build(story)
    return file_path
