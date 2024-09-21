import re

def get_text_width(font, text):
    width = 0
    for char in text:
        bbox = font.getbbox(char)
        char_width = bbox[2] - bbox[0]
        width += char_width
    return width