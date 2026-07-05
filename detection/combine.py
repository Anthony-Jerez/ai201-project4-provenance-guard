from detection.stylometry import MIN_WORDS_FOR_STYLOMETRY

AI_THRESHOLD = 0.70
HUMAN_THRESHOLD = 0.35
DISAGREEMENT_DEVIATION = 0.15
LLM_WEIGHT = 0.65
STYLE_WEIGHT = 0.35


def llm_to_p(llm_result):
    verdict = llm_result["verdict"]
    confidence = llm_result["llm_confidence"]
    if verdict == "ai":
        return 0.5 + 0.5 * confidence
    if verdict == "human":
        return 0.5 - 0.5 * confidence
    return 0.5


def combine_signals(p_llm, p_style):
    p_combined = LLM_WEIGHT * p_llm + STYLE_WEIGHT * p_style

    dev_llm = p_llm - 0.5
    dev_style = p_style - 0.5
    dampened = (
        dev_llm * dev_style < 0
        and abs(dev_llm) > DISAGREEMENT_DEVIATION
        and abs(dev_style) > DISAGREEMENT_DEVIATION
    )
    if dampened:
        p_combined = 0.5 + (p_combined - 0.5) * 0.5

    return p_combined, dampened


def label_and_confidence(p_combined, word_count):
    if p_combined >= AI_THRESHOLD:
        label = "ai"
    elif p_combined <= HUMAN_THRESHOLD:
        label = "human"
    else:
        label = "uncertain"

    if label == "ai" and word_count < MIN_WORDS_FOR_STYLOMETRY:
        label = "uncertain"

    if label == "ai":
        confidence = 0.80 + 0.19 * ((p_combined - AI_THRESHOLD) / 0.30)
        confidence = max(0.80, min(0.99, confidence))
    elif label == "human":
        confidence = 0.80 + 0.19 * ((HUMAN_THRESHOLD - p_combined) / 0.35)
        confidence = max(0.80, min(0.99, confidence))
    else:
        # Uncertain always displays in [0.50, 0.79], even when the word-count floor overrode an "ai" verdict whose p_combined sits past AI_THRESHOLD
        # (distance is capped at the threshold's own span so it can't extrapolate past the intended ceiling)
        if p_combined >= 0.5:
            distance = min(p_combined - 0.5, AI_THRESHOLD - 0.5)
            confidence = 0.50 + 0.29 * (distance / (AI_THRESHOLD - 0.5))
        else:
            distance = min(0.5 - p_combined, 0.5 - HUMAN_THRESHOLD)
            confidence = 0.50 + 0.29 * (distance / (0.5 - HUMAN_THRESHOLD))
        confidence = max(0.50, min(0.79, confidence))

    return label, round(confidence, 2)
