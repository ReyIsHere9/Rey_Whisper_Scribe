from app.core.normalize_fa import has_persian, normalize_persian


def test_arabic_letters_fold_to_persian():
    assert normalize_persian("علي") == "علی"
    assert normalize_persian("كتاب") == "کتاب"


def test_tatweel_is_removed():
    assert normalize_persian("ســـلام") == "سلام"


def test_spaces_around_punctuation_are_tightened():
    assert normalize_persian("سلام ، خوبی ؟") == "سلام، خوبی؟"


def test_english_is_preserved():
    text = "یه timeline جدید داریم"
    assert "timeline" in normalize_persian(text)


def test_has_persian_detection():
    assert has_persian("سلام")
    assert not has_persian("hello")
