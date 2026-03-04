import numpy as np
import os
import json

class SimpleVectorStore:
    def __init__(self, index_file: str = "vector_index.json"):
        self.index_file = index_file
        self.vectors = []
        self.metadata = []
        self._load()

    def _load(self):
        if os.path.exists(self.index_file):
            try:
                with open(self.index_file, 'r') as f:
                    data = json.load(f)
                    self.vectors = [np.array(v) for v in data.get("vectors", [])]
                    self.metadata = data.get("metadata", [])
            except:
                pass

    def _save(self):
        with open(self.index_file, 'w') as f:
            json.dump({
                "vectors": [v.tolist() for v in self.vectors],
                "metadata": self.metadata
            }, f)

    def _get_embedding(self, text: str):
        # Fallback to a very simple character-based embedding 
        # because we don't have a local embedding model running yet
        # In a real scenario, we'd use mlx_lm or sentence-transformers
        vec = np.zeros(128)
        for i, char in enumerate(text[:128]):
            vec[i] = ord(char) / 255.0
        return vec

    def add_text(self, text: str, meta: dict):
        vec = self._get_embedding(text)
        self.vectors.append(vec)
        self.metadata.append(meta)
        self._save()

    def search(self, query: str, top_k: int = 3):
        if not self.vectors:
            return []
        
        query_vec = self._get_embedding(query)
        similarities = []
        for v in self.vectors:
            # Cosine similarity
            sim = np.dot(query_vec, v) / (np.linalg.norm(query_vec) * np.linalg.norm(v) + 1e-9)
            similarities.append(sim)
        
        indices = np.argsort(similarities)[-top_k:][::-1]
        return [self.metadata[i] for i in indices]

if __name__ == "__main__":
    store = SimpleVectorStore("test_vector.json")
    store.add_text("Gujarat is a state in India", {"content": "Gujarat info"})
    print(store.search("Where is Gujarat?"))
