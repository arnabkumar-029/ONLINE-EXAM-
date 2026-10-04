import json
from app import app
from flask import render_template

def test_compact_descriptive_view():
    qs = json.load(open('questions.json', encoding='utf-8'))
    with app.test_request_context():
        html = render_template(
            'all_questions.html',
            questions=qs,
            filter_courses=[],
            filter_course_names=[],
            filter_subjects=[],
            filter_programs=[],
            filter_admission_years=[],
            filter_academic_years=[],
            filter_units=[]
        )

    descs = [q for q in qs if q.get('type') == 'DESCRIPTIVE']
    mcqs = [q for q in qs if q.get('type') == 'MCQ']
    print(f"Total questions: {len(qs)}")
    print(f"Descriptive questions: {len(descs)}")
    print(f"MCQ questions: {len(mcqs)}")

    short_descs = [
        q for q in descs
        if len(q.get('answer_key', '').strip()) <= 120 and (
            '\n' not in q.get('answer_key', '').strip() or
            len(q.get('answer_key', '').strip().split('\n')) <= 3
        )
    ]
    long_descs = [
        q for q in descs
        if len(q.get('answer_key', '').strip()) > 120 or (
            '\n' in q.get('answer_key', '').strip() and
            len(q.get('answer_key', '').strip().split('\n')) > 3
        )
    ]

    print(f"Short descriptive count: {len(short_descs)}")
    print(f"Long descriptive count: {len(long_descs)}")

    short_class_count = html.count('class="qb-desc-short"')
    wrap_class_count = html.count('class="qb-desc-wrap"')
    btn_class_count = html.count('class="qb-btn-toggle-answer"')
    view_more_count = html.count('VIEW MORE &rarr;')

    print(f"HTML class='qb-desc-short' count: {short_class_count}")
    print(f"HTML class='qb-desc-wrap' count: {wrap_class_count}")
    print(f"HTML class='qb-btn-toggle-answer' count: {btn_class_count}")
    print(f"HTML 'VIEW MORE &rarr;' count: {view_more_count}")

    assert short_class_count == len(short_descs), f"Mismatch in short descs: {short_class_count} vs {len(short_descs)}"
    assert wrap_class_count == len(long_descs), f"Mismatch in long descs: {wrap_class_count} vs {len(long_descs)}"
    assert btn_class_count == len(long_descs), f"Mismatch in toggle buttons: {btn_class_count} vs {len(long_descs)}"
    # Note: 'VIEW MORE &rarr;' appears in the button template for each long desc plus in the JS toggle fallback (1 extra)
    assert view_more_count == len(long_descs) + 1, f"Mismatch in VIEW MORE count: {view_more_count} vs {len(long_descs) + 1}"

    # Verify all descriptive answers are fully present in HTML without truncation
    for i, q in enumerate(descs):
        ans = q.get('answer_key', '').strip()
        assert ans[:30] in html, f"Question {q.get('id')} answer snippet not found in HTML!"
        assert ans[-30:] in html, f"Question {q.get('id')} answer end snippet not found in HTML!"

    print("SUCCESS: All descriptive questions render full content correctly with preview wrapper!")

    # Verify MCQ questions still have check badge and correct answer
    assert html.count('fa-circle-check') == len(mcqs), "Mismatch in MCQ check icon count!"
    print("SUCCESS: MCQ questions unaffected and rendered correctly!")

    # Verify CSS and JS are present
    assert '.qb-desc-preview' in html, "Missing .qb-desc-preview CSS"
    assert '-webkit-line-clamp: 4' in html, "Missing line-clamp CSS"
    assert 'toggleDescAnswer' in html, "Missing toggleDescAnswer JS"
    assert 'initDescAnswerPreviews' in html, "Missing initDescAnswerPreviews JS"
    print("SUCCESS: CSS and JS components properly bundled in HTML!")

if __name__ == '__main__':
    test_compact_descriptive_view()
