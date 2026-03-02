# Skill Mind AI: Intelligent Interview Capability Assessment

Skill Mind AI is a production-ready AI-powered web application for real-time interview evaluation and predictive skill mapping.

## 🚀 Features

-   **Resume Analysis**: BERT-based NER for skill extraction.
-   **Technical Quiz**: Dynamic T5 transformer-based question generation.
-   **Coding Assessment**: Abstract Syntax Tree (AST) validation and logic complexity scoring.
-   **AI HR Interview**: Real-time conversational AI using DialoGPT and WebSocket.
-   **Intelligent Scoring**: Weighted aggregation algorithm for readiness reports.

## 🛠️ Tech Stack

-   **Frontend**: HTML5, Modern CSS (Glassmorphism), Vanilla JavaScript.
-   **Backend**: Python Flask, Flask-SocketIO.
-   **AI Implementation**: HuggingFace Transformers (BERT, T5, DialoGPT).
-   **Database**: MySQL.
-   **Authentication**: JWT-based secure session management.

## 📦 Setup Instructions

### Prerequisites
- Python 3.8+
- MySQL Server

### Backend Setup
1. Navigate to `backend/`
2. Create virtual environment: `python -m venv venv`
3. Activate venv: `source venv/bin/activate` (or `venv\Scripts\activate` on Windows)
4. Install dependencies: `pip install -r requirements.txt`
5. Configure `.env` with your MySQL credentials.
6. Run migrations (SQLAlchemy will create tables on first run).
7. Start server: `python run.py`

### Frontend Setup
1. Open `frontend/index.html` in a modern browser (recommended to serve via Live Server or simple HTTP server).

## 📂 Project Structure

```text
skill-mind-ai/
├── backend/
│   ├── app/
│   │   ├── models/       # SQLAlchemy Models
│   │   ├── routes/       # Flask Blueprints
│   │   ├── services/     # AI Inference Logic
│   │   ├── websocket/    # Interview Handlers
│   ├── run.py            # Entry point
│   ├── requirements.txt
├── frontend/             # Modern UI components
└── ai_services/          # Transformer model utils
```
