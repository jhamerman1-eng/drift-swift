#!/usr/bin/env python3
"""
Remove ALL emoji characters from run_swift_mm_complete.py
"""

import re

def remove_emojis(text):
    """Remove emoji characters from text"""
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002700-\U000027BF"  # dingbats
        "\U0001f926-\U0001f937"  # gestures
        "\U00010000-\U0010ffff"  # other unicode
        "\u2640-\u2642"  # gender symbols
        "\u2600-\u2B55"  # misc symbols
        "\u200d"  # zero width joiner
        "\u23cf"  # eject symbol
        "\u23e9"  # fast forward
        "\u231a"  # watch
        "\ufe0f"  # variation selector
        "\u3030"  # wavy dash
        "]+",
        flags=re.UNICODE
    )
    return emoji_pattern.sub('', text)

# Read the file
with open('run_swift_mm_complete.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove ALL emojis from the entire file
content = remove_emojis(content)

# Write back
with open('run_swift_mm_complete.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("ALL emojis removed from run_swift_mm_complete.py!")
