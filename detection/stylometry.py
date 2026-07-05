import re
import statistics

SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
WORD_RE = re.compile(r"[A-Za-z']+")

CONJUNCTIONS = {
    "because", "although", "while", "since", "though", "unless", "whereas",
    "if", "when", "before", "after", "that", "which", "and", "but", "or", "so",
}

MIN_WORDS_FOR_STYLOMETRY = 40


def _clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def _words(s):
    return WORD_RE.findall(s.lower())


def _split_sentences(text):
    return [s.strip() for s in SENTENCE_SPLIT_RE.split(text.strip()) if s.strip()]


def _sentence_length_cv(sentences):
    lengths = [len(_words(s)) for s in sentences]
    lengths = [n for n in lengths if n > 0]
    if len(lengths) < 2 or statistics.mean(lengths) == 0:
        return 0.0
    return statistics.pstdev(lengths) / statistics.mean(lengths)


def _type_token_ratio(words):
    sample = words[:200]
    if not sample:
        return 0.0
    return len(set(sample)) / len(sample)


def _punctuation_variety(text):
    categories = 0
    if "." in text:
        categories += 1
    if "," in text:
        categories += 1
    if ";" in text:
        categories += 1
    if ":" in text:
        categories += 1
    if any(c in text for c in "-–—"):
        categories += 1
    if "..." in text or "…" in text:
        categories += 1
    if "!" in text:
        categories += 1
    if "?" in text:
        categories += 1
    if "(" in text or ")" in text:
        categories += 1
    return categories


def _sentence_complexity_stdev(sentences):
    counts = []
    for s in sentences:
        conj_count = sum(1 for w in _words(s) if w in CONJUNCTIONS)
        comma_count = s.count(",")
        counts.append(conj_count + comma_count)
    if not counts:
        return 0.0
    return statistics.pstdev(counts)


def analyze_stylometry(text):
    sentences = _split_sentences(text)
    words = _words(text)
    word_count = len(words)

    cv = _sentence_length_cv(sentences)
    ttr = _type_token_ratio(words)
    variety = _punctuation_variety(text)
    complexity_stdev = _sentence_complexity_stdev(sentences)

    ai_variance = _clamp(0.5 - (cv - 0.45) / 0.5)
    ai_ttr = _clamp(0.5 - (ttr - 0.80) / 0.40)
    ai_punct = _clamp(0.5 - (variety - 3.5) / 3.0)
    ai_complexity = _clamp(0.5 - (complexity_stdev - 0.8) / 1.2)

    p_style_raw = (
        0.30 * ai_variance + 0.25 * ai_ttr + 0.25 * ai_punct + 0.20 * ai_complexity
    )
    p_style = 0.5 if word_count < MIN_WORDS_FOR_STYLOMETRY else p_style_raw

    return {
        "word_count": word_count,
        "sentence_length_cv": round(cv, 4),
        "ttr": round(ttr, 4),
        "punctuation_variety": variety,
        "complexity_stdev": round(complexity_stdev, 4),
        "ai_variance": round(ai_variance, 4),
        "ai_ttr": round(ai_ttr, 4),
        "ai_punct": round(ai_punct, 4),
        "ai_complexity": round(ai_complexity, 4),
        "p_style": round(p_style, 4),
    }
