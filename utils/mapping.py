import json
import re

with open("static/data/master_tags.json", "r", encoding="utf-8") as f:
    MASTER_TAGS = json.load(f)

def normalize(text):
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text

def map_skin_issues(raw_text):
    # Pisah dengan koma
    issues = [normalize(x) for x in raw_text.split(",")]

    mapped = set()  # Set untuk hilangkan duplikat

    for issue in issues:
        for category, tags in MASTER_TAGS.items():
            for tag in tags:
                # Cocokkan jika tag muncul dalam issue
                if tag in issue:
                    mapped.add(tag)

    return list(mapped)
    