import re
import os

def get_text_width(font, text):
    width = 0
    for char in text:
        bbox = font.getbbox(char)
        char_width = bbox[2] - bbox[0]
        width += char_width
    return width

def load_prompt_template(prompt_filename):
    prompt_path = os.path.join(os.path.dirname(__file__), '..', 'services', 'prompts', prompt_filename)
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read().strip()