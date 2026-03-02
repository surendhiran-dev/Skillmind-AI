import numpy as np

def generate_embedding(text):
    """
    Placeholder for BERT/Sentence-Transformers embedding.
    In a real production environment, this would call a local model or OpenAI/Gemini Embeddings.
    """
    # For now, we simulate a vector
    return np.random.rand(384).tolist()

def calculate_cosine_similarity(vec_a, vec_b):
    """
    Calculates cosine similarity between two vectors.
    """
    a = np.array(vec_a)
    b = np.array(vec_b)
    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    return dot_product / (norm_a * norm_b)
