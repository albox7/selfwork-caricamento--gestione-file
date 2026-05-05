import re
import numpy as np
from langchain_openai import OpenAIEmbeddings
from sklearn.metrics.pairwise import cosine_similarity


class SemanticChunking:
    def __init__(self, api_key, breakpoint_percentile=95, buffer_size=1):
        # self.embeddings = OpenAIEmbeddings(openai_api_key=api_key)
        self.embeddings = OpenAIEmbeddings(openai_api_key=api_key, model="text-embedding-3-small")

        self.breakpoint_percentile = breakpoint_percentile
        self.buffer_size = buffer_size

    def _split_into_sentences(self, text):
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())

        if len(sentences) == 1 and len(text) > 100:
            delimiters = r"([.!?\n;:])"
            parts = re.split(delimiters, text.strip())

            sentences = []
            for i in range(0, len(parts) - 1, 2):
                if parts[i].strip():
                    sentences.append(parts[i].strip() + parts[i + 1])

            if len(sentences) == 1:
                sentences = [s.strip() + "," for s in text.split(",") if s.strip()]
                if sentences:
                    sentences[-1] = sentences[-1][:-1] + "."

        sentences = [s for s in sentences if s.strip()]
        if not sentences:
            sentences = [text + "."]

        return sentences

    def _process_sentences(self, text):
        raw_sentences = self._split_into_sentences(text)
        sentences = [{"sentence": s, "index": i} for i, s in enumerate(raw_sentences)]

        for i, current in enumerate(sentences):
            context_range = range(
                max(0, i - self.buffer_size),
                min(len(sentences), i + self.buffer_size + 1),
            )
            current["combined_sentence"] = " ".join(
                sentences[j]["sentence"] for j in context_range
            )

        return sentences

    def _calculate_distances(self, sentences):
        embeddings = self.embeddings.embed_documents(
            [s["combined_sentence"] for s in sentences]
        )

        distances = []
        for i in range(len(sentences) - 1):
            distance = 1 - cosine_similarity([embeddings[i]], [embeddings[i + 1]])[0][0]
            distances.append(distance)

        return distances

    def chunk_text(self, text):
        sentences = self._process_sentences(text)

        if not sentences:
            return [text]

        distances = self._calculate_distances(sentences)

        if not distances:
            return [text]

        threshold = np.percentile(distances, self.breakpoint_percentile)
        split_points = [i for i, d in enumerate(distances) if d > threshold]

        chunks = []
        start = 0
        for point in split_points + [len(sentences) - 1]:
            chunk = " ".join(s["sentence"] for s in sentences[start : point + 1])
            chunks.append(chunk)
            start = point + 1

        return chunks