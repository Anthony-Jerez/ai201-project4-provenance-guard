LABEL_TEXT = {
    "ai": (
        "This content is likely AI-generated (confidence: high). Our system found "
        "strong, consistent signals of AI authorship across both semantic analysis "
        "and writing-pattern analysis. If you believe this is incorrect, you can "
        "appeal this decision."
    ),
    "human": (
        "This content appears to be human-written (confidence: high). Our checks "
        "found no strong indicators of AI generation."
    ),
    "uncertain": (
        "We can't confidently determine whether this was written by a person or AI. "
        "This is not an accusation. Our signals simply didn't agree strongly enough "
        "to make a call. If you have context that would help, you're welcome to "
        "appeal."
    ),
}


def generate_transparency_message(label):
    return LABEL_TEXT[label]
