# src/pdf_generation.py
def simpleSplit(text, font, size, max_width):
    lines = []
    words = text.split(" ")
    current_line = ""

    for word in words:
        test_line = f"{current_line} {word}".strip()
        if len(test_line) * size < max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)
    return lines