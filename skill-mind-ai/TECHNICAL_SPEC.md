# Skill Mind AI: Technical Specifications

This document outlines the theoretical grounding, mathematical models, and architectural modules powering the Skill Mind AI platform.

---

## 🔐 1. User Management Module
**Key Functions**: Registration, Secure Login, JWT Auth, Session Management, Role-Based Access Control (RBAC).

### Module Diagram
```mermaid
graph LR
    User --> Login["Login/Register Page"]
    Login --> API["Backend API"]
    API --> DB[(Database)]
    API --> JWT[JWT Token Generated]
    JWT --> Session[Authenticated Session]
```

---

## 🧠 2. Resume Analysis Module
**Algorithm**: BERT + Named Entity Recognition (NER)
**Key Functions**: Upload (PDF/TXT), Text Extraction, BERT (NER) for Skills/Ed/Exp, Structured Storage.

### Module Diagram
```mermaid
graph TD
    Upload[Resume Upload] --> Extract[Text Extraction]
    Extract --> BERT[BERT + NER Model]
    BERT --> Storage[(Structured Skills Stored in DB)]
```

### Self-Attention Equation
$$Attention(Q, K, V) = \text{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V$$

---

## 🧠 3. Quiz Generation Module
**Algorithm**: T5 (Text-to-Text Transformer)
**Key Functions**: Skill analysis, T5 Question generation, Real-time MCQ scoring.

### Module Diagram
```mermaid
graph TD
    Skills[Extracted Skills] --> T5[T5 Transformer]
    T5 --> Questions[Generated Questions]
    Questions --> Scoring[User Answers & Score Storage]
```

### Encoder–Decoder Probability
$$P(Y|X) = \prod_{t=1}^{n} P(y_t | y_{<t}, X)$$

---

## 🧠 4. Coding Assessment Module
**Algorithm**: Transformer-Based Autoregressive Model
**Key Functions**: Question generation, Code input acceptance, Autoregressive evaluation, Syntax/Logic scoring.

### Module Diagram
```mermaid
graph TD
    CQ[Coding Question] --> Code[User Code Submission]
    Code --> Model[Transformer Model]
    Model --> Eval[Logic & Syntax Evaluation]
    Eval --> Score[Coding Score]
```

---

## 🧠 5. AI HR Interview Module
**Algorithm**: Instruction-Tuned Transformer + RLHF
**Key Functions**: Face-to-face simulation, Context-aware conversation, Dynamic follow-ups, Communication evaluation.

### Module Diagram
```mermaid
graph TD
    Resp[User Response] --> Inst[Instruction-Tuned Transformer]
    Inst --> RLHF[RLHF Optimization]
    RLHF --> Next[Next HR Question]
    Next --> Score[Communication Score]
```

---

## 📊 6. Evaluation & Scoring Module
**Key Functions**: Semantic Similarity (Cosine), Weighted Aggregation, Final Readiness Score.

### Module Diagram
```mermaid
graph TD
    QS[Quiz Score] --> Agg[Weighted Aggregation]
    CS[Coding Score] --> Agg
    HS[HR Score] --> Agg
    RS[Resume Score] --> Agg
    Agg --> Final[Final Interview Readiness Score]
```

### Weighted Aggregation Formula
$$\text{Final Score} = 0.3(Q) + 0.3(C) + 0.3(H) + 0.1(R)$$

---

## 📈 7. Skill Gap Prediction Module
**Key Functions**: Performance mapping, Weak/Strong identification, Threshold classification, Suggestions.

### Module Diagram
```mermaid
graph TD
    FS[Final Scores] --> Rule[Rule-Based Classification]
    Rule --> Levels[Strong / Moderate / Weak]
    Levels --> Report[Skill Gap Report]
```

---

## 📱 8. Dashboard & Analytics Module
**Key Functions**: Readiness Score display, Progress tracking, Visual reports (Charts), Performance downloads.

### Module Diagram
```mermaid
graph TD
    DB[(Database)] --> Engine[Analytics Engine]
    Engine --> Charts[Charts & Reports]
    Charts --> Dash[User Dashboard]
```
