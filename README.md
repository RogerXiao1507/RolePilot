# RolePilot

link to website: https://rolepilot-nu.vercel.app/?jr_id=69a677a1d706a731db3865db

RolePilot is an AI powered career copilot that helps users track job and internship applications, analyze resumes, compare resumes against job postings, generate tailored resume content, and export polished resume drafts.

It goes beyond a basic application tracker by combining structured application management with AI powered resume analysis, semantic retrieval, and grounded resume tailoring.

## Features

### Application tracking
- Create, edit, delete, and view applications
- Track company, role title, status, location, job URL, and job description
- View dashboard summary cards for total, saved, applied, interview, and offer

### AI job parsing
- Paste a raw job description and extract structured job data
- Paste a job posting URL and parse it automatically
- Save parsed company, role title, location, required skills, preferred skills, keywords, summary, and next steps

### Resume analysis
- Upload a PDF resume
- Extract text and analyze:
  - strengths
  - weaknesses
  - wording issues
  - missing metrics
  - suggested improvements

### Resume to job matching
- Compare the saved resume against a target application
- Generate:
  - overall match summary
  - matched skills
  - missing skills
  - strengths for role
  - improvement areas
  - suggested resume changes

### RAG based resume tailoring
- Save structured project evidence
- Chunk project evidence into smaller retrievable units
- Generate embeddings for chunks
- Store embeddings in PostgreSQL using pgvector
- Retrieve semantically relevant evidence for a target application
- Generate grounded tailored resume content using:
  - saved resume
  - application job data
  - retrieved project evidence

### Tailored resume generation
- Generate tailored bullets and skill emphasis for a specific application
- Build a full tailored resume draft in a consistent serif resume format
- Persist the full draft per application
- Export the final draft as DOCX and PDF

## Tech stack

### Frontend
- Next.js
- TypeScript
- Tailwind CSS

### Backend
- FastAPI
- SQLAlchemy
- PostgreSQL
- pgvector
- OpenAI API
- python-docx

### AI / Retrieval
- OpenAI Responses API
- OpenAI embeddings
- Semantic retrieval with pgvector
- RAG pipeline for grounded tailoring

## How it works

RolePilot uses a retrieval augmented generation workflow for tailored resume generation:

1. The user uploads a resume and saves project evidence
2. Project evidence is chunked and embedded
3. Embeddings are stored in PostgreSQL with pgvector
4. When the user tailors a resume for a job, RolePilot builds a query from:
   - role title
   - AI job summary
   - job description
   - required skills
   - preferred skills
   - keywords
5. The system retrieves the most semantically relevant evidence chunks
6. The model generates tailored bullets and a full resume draft grounded in the retrieved evidence

## Architecture overview

### Backend modules
- `applications` for CRUD application tracking
- `resume` for upload, analysis, and persistence
- `project-evidence` for evidence storage
- `ai` for parsing, matching, tailoring, and full draft generation
- `export` for DOCX and PDF generation

### Data flow
- Resume PDF upload -> text extraction -> AI analysis -> saved resume
- Job description / URL -> structured job parsing -> saved application
- Application + saved resume + retrieved evidence -> tailored resume content
- Tailored content -> full draft generation -> DOCX / PDF export

## Project structure

```bash
RolePilot/
├── backend/
│   ├── app/
│   │   ├── api/routes/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── services/
│   └── .venv/
├── frontend/
│   ├── app/
│   ├── lib/
│   └── public/
└── README.md

