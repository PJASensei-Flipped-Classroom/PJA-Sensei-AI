from app.application.response_pipeline import IncrementalAnswerExtractor


def test_incremental_answer_extractor_live_chunks():
    ex = IncrementalAnswerExtractor()
    parts = [
        '{"prompt_score": 5, "answer": "Hel',
        "lo ",
        "świecie",
        '\\nlinia',
        ' 2", "penalty_applied": false}',
    ]
    seen = ""
    for p in parts:
        seen += ex.feed(p)
    assert seen == "Hello świecie\nlinia 2"
    assert ex.answer_so_far == "Hello świecie\nlinia 2"


def test_incremental_answer_first_field():
    ex = IncrementalAnswerExtractor()
    assert ex.feed('{"answer": "A') == "A"
    assert ex.feed("BC") == "BC"
    assert ex.feed('"}') == ""
    assert ex.answer_so_far == "ABC"


def test_incomplete_unicode_escape_waits():
    ex = IncrementalAnswerExtractor()
    assert ex.feed('{"answer": "x\\u') == "x"
    assert ex.feed("00") == ""
    assert ex.feed('61"') == "a"
    assert ex.answer_so_far == "xa"
