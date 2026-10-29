"""Trechos Markdown com metadados de seção, além de recuperação TF-IDF."""
from dataclasses import dataclass
from pathlib import Path
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass(frozen=True)
class Passage:
    source: str
    text: str
    score: float = 0.0
    section: str = ""
    score_kind: str = "semantic"


class KnowledgeBase:
    def __init__(self, path: Path):
        self.passages: list[Passage] = []
        for file in sorted(Path(path).glob("*.md")):
            section = ""
            content = file.read_text(encoding="utf-8")
            for paragraph in content.split("\n\n"):
                cleaned = " ".join(paragraph.split()).strip()
                if cleaned.startswith("## "):
                    section = cleaned[3:]
                elif len(cleaned) > 50 and not cleaned.startswith("# "):
                    self.passages.append(Passage(source=file.name, text=cleaned, section=section))
        self.vectorizer = TfidfVectorizer(strip_accents="unicode", ngram_range=(1, 2), lowercase=True)
        self.matrix = self.vectorizer.fit_transform([p.text for p in self.passages]) if self.passages else None

    def search(self, query: str, top_k: int = 3, threshold: float = 0.085) -> list[Passage]:
        if self.matrix is None or not query.strip():
            return []
        # Expansões transparentes de variações frequentes em linguagem natural.
        # A base é pequena e o índice é documental, não um corretor linguístico geral.
        expanded = query
        expansions = (
            (r'extraviad[ao]s?|extraviar|desapareceu|sumiu|perdeu a carga', ' extravio'),
            (r'danificad[ao]s?|quebrada', ' avaria'),
            (r'atrasad[ao]s?', ' atraso'),
        )
        for pattern, term in expansions:
            if re.search(pattern, query, re.IGNORECASE):
                expanded += term
        scores = cosine_similarity(self.vectorizer.transform([expanded]), self.matrix).ravel()
        ordered = sorted(enumerate(scores), key=lambda row: (-row[1], row[0]))
        return [Passage(self.passages[i].source, self.passages[i].text, round(float(score), 4), self.passages[i].section, "tfidf")
                for i, score in ordered[:top_k] if score >= threshold]
