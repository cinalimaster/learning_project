import itertools
from typing import List, Dict


class AdvancedDocumentSplitter:
    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64):
        self.chunk_size = max(64, chunk_size)
        self.chunk_overlap = max(0, min(chunk_overlap, self.chunk_size // 2))

    def split_document(self, text: str, title: str = "") -> List[Dict]:
        words = text.split()
        chunks: List[Dict] = []

        if not words:
            return [{'id': '0', 'text': '', 'section_title': title}]

        start = 0
        chunk_id = 0
        while start < len(words):
            end = min(len(words), start + self.chunk_size)
            chunk_words = words[start:end]
            chunk_text = " ".join(chunk_words)
            chunks.append({
                'id': str(chunk_id),
                'text': chunk_text,
                'section_title': title,
            })
            if end == len(words):
                break
            start = end - self.chunk_overlap
            chunk_id += 1

        return chunks

