# FineAnalyst
*Ask your data questions. Get the analysis.*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Next.js](https://img.shields.io/badge/Next.js-16.2-black?logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Pydantic-AI](https://img.shields.io/badge/Pydantic--AI-2.22-e92063)](https://pydantic.dev/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-4.3-38B2AC?logo=tailwind-css)](https://tailwindcss.com/)

FineAnalyst is an intelligent analytical workspace that allows users to interact with structured datasets through natural language. Instead of simply generating SQL strings, FineAnalyst implements an end-to-end analytical pipeline: understanding analytical intent, executing queries safely against an application database, validating the results, and dynamically rendering the most appropriate visualization.

It was built from the ground up by **FineWorks** to provide a robust, chat-based BI experience.

---

## The Problem

Most organizations possess massive amounts of data, but the barrier to entry isn't having the data—it's knowing how to query it, what to ask, and how to interpret the results.

Traditional analytics workflows require:
- Deep knowledge of SQL and underlying schemas
- Manually creating and running queries
- Switching context between a database IDE, charting tools, and presentation software
- Interpreting raw, unformatted tabular data

FineAnalyst aims to make interacting with data conversational, while keeping the analytical pipeline grounded in actual datasets rather than LLM hallucinations.

---

## The Core Idea

FineAnalyst isn't just an "AI that writes SQL". It is an engineered pipeline that maps natural language to a deterministic analytical workflow.

```text
User Question
      ↓
Intent Understanding (Conversation vs. Analytics)
      ↓
Schema Discovery & Mapping
      ↓
SQL Generation
      ↓
Query Execution (via SQLAlchemy/SQLite)
      ↓
Validation & Fallback Handling
      ↓
Insight Generation + Dynamic Visualization (Mermaid / Recharts)
```

---

## From Question → Answer

Here is a practical example of how FineAnalyst processes a user request.

**User:**
> *"Compare our monthly revenue and expenses."*

**FineAnalyst:**
1. **Understands Intent:** Identifies the request as an analytical database query.
2. **Schema Discovery:** Scans the SQLite database for relevant tables (`transactions`, `revenue`, etc.).
3. **Query Generation:** Writes the correct SQL query to aggregate monthly revenue and expenses.
4. **Execution:** Runs the query securely against the database.
5. **Validation:** Checks if the returned data matches the expected format (preventing hallucinated columns).
6. **Visualization:** Identifies that time-series comparison data is best represented as a multi-line or bar chart, passing the optimal configuration to the frontend Mermaid/Recharts renderer.
7. **Insight:** Generates an executive summary and KPIs based *only* on the executed data.

---

## Why It's Different: Engineering Decisions

We focused on building a durable application rather than a thin LLM wrapper. Here are a few key engineering decisions implemented in the repository:

- **Intent Routing:** Questions like *"What database do you have?"* or *"Who created you?"* are deterministically intercepted as application meta-questions. They do not trigger expensive SQL generation pipelines.
- **True Request Cancellation:** The chat interface implements a ChatGPT-style "Stop" button. We use `AbortController` on the frontend, and the FastAPI backend explicitly catches `asyncio.CancelledError`, immediately halting orchestration and saving tokens.
- **Persistent Authentication:** Full JWT-based auth (with secure `bcrypt` hashed passwords via `pbkdf2_hmac` and salting) is built-in. Your session and conversation history persist across browser restarts, securely scoped to your `user_id`.
- **Dynamic Mermaid Rendering:** Mermaid charts are heavily optimized. They are lazy-loaded via Next.js dynamic imports (`next/dynamic`) so the massive charting engine only executes when a visualization is actually requested, keeping the frontend bundle small and fast.
- **Robust Rate Limiting:** The backend gracefully catches LLM provider rate limits (HTTP 429) and surfaces them as friendly UI toasts, rather than crashing the application or returning 500 Server Errors.
- **Responsive Architecture:** The UI is built with a mobile-first approach using Tailwind CSS. Modals, chat bubbles, and even complex data-grids scale seamlessly down to 320px screens without horizontal scroll-locking.

---

## Architecture & Tech Stack

### Frontend
- **Framework:** Next.js 16 (App Router)
- **Styling:** Tailwind CSS v4, Framer Motion, Radix UI
- **State Management:** Zustand (with local storage persistence)
- **Visualizations:** Mermaid.js, Recharts, React Data Grid

### Backend
- **Framework:** FastAPI (Asynchronous)
- **Database:** SQLite with SQLAlchemy ORM and Alembic for migrations
- **AI/LLM Orchestration:** Pydantic-AI for structured LLM responses and predictable output parsing
- **Security:** JWT authentication, rate-limiting (slowapi), pbkdf2 password hashing

---

## Run It Locally

### 1. Start the Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# Create a .env file and add your AI provider keys (e.g., GROQ_API_KEY)
uvicorn app.main:app --reload --port 8000
```

### 2. Start the Frontend
```bash
cd frontend
npm install
npm run dev
```

The application will be available at `http://localhost:3000`.

---

## The FineWorks Team

FineAnalyst was created by **FineWorks**, a project-oriented technology team building solutions across software engineering, artificial intelligence, and data analysis.

**Core Team:**
- Saranesh
- Praveen Balaji
- Nitish
- Sakthi Saran
