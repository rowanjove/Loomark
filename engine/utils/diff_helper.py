import difflib
from typing import List, Dict, Any

def compute_text_diff(old_text: str, new_text: str) -> List[Dict[str, Any]]:
    """
    Compute structured line-by-line diff between two text versions (PRD Section 73).
    Returns list of line objects with type: 'equal', 'insert', or 'delete'.
    """
    old_lines = (old_text or "").splitlines()
    new_lines = (new_text or "").splitlines()

    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
    diff_entries = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for idx, line in enumerate(old_lines[i1:i2]):
                diff_entries.append({
                    "type": "equal",
                    "text": line,
                    "old_num": i1 + idx + 1,
                    "new_num": j1 + idx + 1
                })
        elif tag == "delete":
            for idx, line in enumerate(old_lines[i1:i2]):
                diff_entries.append({
                    "type": "delete",
                    "text": line,
                    "old_num": i1 + idx + 1,
                    "new_num": None
                })
        elif tag == "insert":
            for idx, line in enumerate(new_lines[j1:j2]):
                diff_entries.append({
                    "type": "insert",
                    "text": line,
                    "old_num": None,
                    "new_num": j1 + idx + 1
                })
        elif tag == "replace":
            for idx, line in enumerate(old_lines[i1:i2]):
                diff_entries.append({
                    "type": "delete",
                    "text": line,
                    "old_num": i1 + idx + 1,
                    "new_num": None
                })
            for idx, line in enumerate(new_lines[j1:j2]):
                diff_entries.append({
                    "type": "insert",
                    "text": line,
                    "old_num": None,
                    "new_num": j1 + idx + 1
                })

    return diff_entries
