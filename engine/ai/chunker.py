import re
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

def split_text_into_chunks(
    text: str,
    max_chunk_chars: int = 3500,
    overlap_chars: int = 200
) -> List[Dict[str, Any]]:
    """
    Split large text into coherent semantic chunks by paragraphs or punctuation
    (PRD Section 45 Chunk System).
    """
    if not text or not text.strip():
        return []

    if len(text) <= max_chunk_chars:
        return [{
            "chunk_index": 0,
            "text": text.strip(),
            "char_count": len(text.strip()),
            "token_count": len(text.strip()) // 4
        }]

    # Split by paragraphs and sub-split by sentence delimiters if any part exceeds max_chunk_chars
    sub_parts = []
    for part in re.split(r'(\n\s*\n)', text):
        if not part:
            continue
        if len(part) > max_chunk_chars:
            sentences = re.split(r'([。！？\.\!\?]\s*)', part)
            sub_curr = ""
            for s in sentences:
                if len(sub_curr) + len(s) > max_chunk_chars:
                    if sub_curr:
                        sub_parts.append(sub_curr)
                    if len(s) > max_chunk_chars:
                        for idx in range(0, len(s), max_chunk_chars):
                            sub_parts.append(s[idx:idx+max_chunk_chars])
                        sub_curr = ""
                    else:
                        sub_curr = s
                else:
                    sub_curr += s
            if sub_curr:
                sub_parts.append(sub_curr)
        else:
            sub_parts.append(part)

    chunks = []
    current_chunk = []
    current_len = 0

    for part in sub_parts:
        if not part:
            continue
        part_len = len(part)
        if current_len + part_len > max_chunk_chars and current_chunk:
            combined = "".join(current_chunk).strip()
            chunks.append({
                "chunk_index": len(chunks),
                "text": combined,
                "char_count": len(combined),
                "token_count": len(combined) // 4
            })
            overlap = combined[-overlap_chars:] if len(combined) > overlap_chars else ""
            current_chunk = [overlap, part] if overlap else [part]
            current_len = len(overlap) + part_len
        else:
            current_chunk.append(part)
            current_len += part_len

    if current_chunk:
        combined = "".join(current_chunk).strip()
        if combined:
            chunks.append({
                "chunk_index": len(chunks),
                "text": combined,
                "char_count": len(combined),
                "token_count": len(combined) // 4
            })

    return chunks

async def summarize_large_text(
    ai_client,
    text: str,
    title: str = "",
    model: Optional[str] = None
) -> Dict[str, Any]:
    """
    Hierarchical summarization for oversized documents:
    Document -> Chunks -> Chunk Summaries -> Document Summary
    """
    chunks = split_text_into_chunks(text, max_chunk_chars=4000)
    if len(chunks) <= 1:
        return await ai_client.execute_task("article_summary_v1", text, title=title, model=model)

    chunk_summaries = []
    total_in_tokens = 0
    total_out_tokens = 0
    total_cost = 0.0

    for chunk in chunks:
        res = await ai_client.execute_task(
            "article_summary_v1",
            content=chunk["text"],
            title=f"{title} (Part {chunk['chunk_index'] + 1})",
            model=model
        )
        if "error" not in res:
            res_text = res["result"].get("text", "")
            chunk_summaries.append(f"【分段 {chunk['chunk_index'] + 1} 要点】:\n{res_text}")
            total_in_tokens += res.get("input_tokens", 0)
            total_out_tokens += res.get("output_tokens", 0)
            total_cost += res.get("cost", 0.0)

    # Aggregate summaries
    combined_notes = "\n\n".join(chunk_summaries)
    final_res = await ai_client.execute_task(
        "article_summary_v1",
        content=combined_notes,
        title=f"{title} 全篇汇编",
        model=model
    )
    final_res["input_tokens"] = total_in_tokens + final_res.get("input_tokens", 0)
    final_res["output_tokens"] = total_out_tokens + final_res.get("output_tokens", 0)
    final_res["cost"] = round(total_cost + final_res.get("cost", 0.0), 5)
    return final_res

def process_and_save_chunks(
    repo,
    document_id: str,
    project_id: str,
    text: str,
    max_chunk_chars: int = 3000
) -> List[Dict[str, Any]]:
    """
    Split document text and persist chunks into SQLite chunks table (PRD Section 45, 52).
    """
    existing = repo.get_document_chunks(document_id)
    if existing:
        return existing

    chunks = split_text_into_chunks(text, max_chunk_chars=max_chunk_chars)
    saved = []
    for c in chunks:
        cid = repo.create_chunk(
            document_id=document_id,
            project_id=project_id,
            chunk_index=c["chunk_index"],
            text=c["text"],
            char_count=c["char_count"],
            token_count=c["token_count"],
            summary=c.get("summary")
        )
        saved.append({
            "id": cid,
            "document_id": document_id,
            "project_id": project_id,
            "chunk_index": c["chunk_index"],
            "text": c["text"],
            "char_count": c["char_count"],
            "token_count": c["token_count"],
            "summary": c.get("summary")
        })
    return saved

