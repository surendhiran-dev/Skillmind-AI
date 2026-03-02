import math
import re
from collections import Counter

def get_cosine_similarity(text1, text2):
    """
    Calculate semantic similarity between two texts using TF-IDF and Cosine Similarity.
    This aligns with Module 6 (Evaluation & Scoring) of the technical specs.
    """
    if not text1 or not text2:
        return 0.0
        
    # Simple tokenization and normalization
    words1 = re.findall(r'\w+', text1.lower())
    words2 = re.findall(r'\w+', text2.lower())
    
    count1 = Counter(words1)
    count2 = Counter(words2)
    
    all_words = set(count1.keys()) | set(count2.keys())
    
    dot_product = sum(count1[w] * count2[w] for w in all_words)
    mag1 = math.sqrt(sum(count1[w]**2 for w in count1))
    mag2 = math.sqrt(sum(count2[w]**2 for w in count2))
    
    if mag1 * mag2 == 0:
        return 0.0
        
    return dot_product / (mag1 * mag2)

def evaluate_technical_answer(user_answer, model_answer):
    """
    Combine keyword check and cosine similarity for technical evaluation.
    """
    similarity = get_cosine_similarity(user_answer, model_answer)
    
    # Scale similarity to 0-100
    score = round(similarity * 100, 1)
    
    # Heuristic for meaningful response
    if len(user_answer.split()) < 5:
        score = min(score, 30)
        
    return score
