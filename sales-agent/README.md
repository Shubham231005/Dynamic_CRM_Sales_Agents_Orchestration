# Intelligent Multi-Agent AI Sales Automation System

## Project Overview
The Intelligent Multi-Agent AI Sales Automation System aims to automate the end-to-end B2B sales pipeline, from lead generation and scoring to outreach and follow-up. 

**Current Scope: Integration 1 (MVP)**
This first integration focuses strictly on the foundational Lead Generation pipeline. It allows fetching leads from a provider, cleaning and validating the data, removing duplicates, and storing the results in a local SQLite database, all exposed via a FastAPI REST API.

## Architecture
The system uses a modular, provider-agnostic architecture:

```
User API Request -> LeadGenerationAgent
                        |
                        v
                 BaseLeadProvider (Interface)
                 /                   \
        MockLeadProvider     GoogleMapsProvider (Placeholder)
                 \                   /
                  v                 v
                 Data Cleaner & Validator
                        |
                        v
                   LeadService
                        |
                        v
                 SQLite Database
```

## Tech Stack
- **Backend Framework:** FastAPI, Uvicorn
- **Language:** Python 3.11+
- **Database ORM:** SQLAlchemy, Pydantic
- **Database:** SQLite
- **Testing:** pytest

## Installation & Setup

1. **Clone the repository and enter the directory:**
   ```bash
   cd sales-agent
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables:**
   Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
   (The defaults use a local SQLite database: `sqlite:///./sales_agent.db`)

## Running the Application

Run the server using the provided script:
```bash
python run.py
```
Or directly with Uvicorn:
```bash
uvicorn app.main:app --reload
```

The API docs will be available at: [http://localhost:8000/docs](http://localhost:8000/docs)

## API Endpoints & Examples

### 1. Generate Leads
**POST** `/api/leads/generate`

*Request:*
```json
{
    "industry": "Dental Clinics",
    "location": "Mumbai",
    "max_results": 10,
    "provider": "mock"
}
```

*Response:*
```json
{
    "success": true,
    "total_found": 10,
    "new_leads": 10,
    "duplicates": 0,
    "leads": [
        {
            "company_name": "Bright Smiles Dental Clinic",
            "industry": "Dental Clinics",
            ...
        }
    ]
}
```

### 2. Get Leads
**GET** `/api/leads`
(Supports optional query params: `industry`, `location`, `status`, `skip`, `limit`)

### 3. Get Lead by ID
**GET** `/api/leads/{lead_id}`

### 4. Delete Lead
**DELETE** `/api/leads/{lead_id}`

## Running Tests

The test suite covers data cleaning, data validation, mock provider logic, duplicate detection, and the API endpoints.

```bash
pytest tests/
```

## Current Limitations
- **No real web scraping yet:** The `GoogleMapsProvider` is currently a placeholder (returns 501 Not Implemented). The `MockLeadProvider` is fully functional and should be used to test the pipeline.
- **Single Agent:** Only the `LeadGenerationAgent` is implemented.

## Team Assignments & Workflow

To ensure smooth orchestration and avoid merge conflicts, we have divided the responsibilities and set up a dedicated Git branching strategy for the team: **Shubham**, **Lavanya**, and **Akshat**.

### 1. Shubham
**Role:** Lead AI & Pipeline Developer
**Branch:** `shubham-dev`
**What Shubham has done till now:**
- Architected the foundational Lead Generation pipeline.
- Built the initial Web Discovery Agent and AI Lead Research Pipeline (including source validation and heuristic scoring).
- Implemented the FastAPI backend, MockLeadProvider, local SQLite database integration, and test suites.
- Set up the project structure and initial repository orchestration.

**Shubham's Git Commands:**
```bash
# Pull latest changes from your branch
git checkout shubham-dev
git pull origin shubham-dev

# Push your work
git add .
git commit -m "Your commit message"
git push origin shubham-dev
```

### 2. Lavanya
**Role:** Communications & Outreach Developer
**Branch:** `lavanya-dev`
**What Lavanya has to do:**
- Implement the Multi-Channel Sales Automation (Email, WhatsApp, Instagram DM, Telegram).
- Develop the Email Agent to draft personalized outreach based on scraped data.
- Build the Follow-up Agent to handle responses, scheduling, and tracking open rates.
- Ensure API credentials and connectivity for communication channels are securely managed.

**Lavanya's Git Commands:**
```bash
# First time fetching the branch
git fetch origin
git checkout lavanya-dev

# Daily workflow to pull latest changes
git pull origin lavanya-dev

# Push your work
git add .
git commit -m "Lavanya: added email agent functionality"
git push origin lavanya-dev
```

### 3. Akshat
**Role:** Orchestrator & Scoring Developer
**Branch:** `akshat-dev`
**What Akshat has to do:**
- Develop the **Orchestrator Agent** to manage the flow and state between all the different agents (Discovery -> Scoring -> Outreach).
- Build the Lead Scoring Agent to analyze and rank leads based on the data provided by Shubham's research pipeline.
- Work on database scalability and ensuring that the structured Company Profiles are correctly passed between agents.

**Akshat's Git Commands:**
```bash
# First time fetching the branch
git fetch origin
git checkout akshat-dev

# Daily workflow to pull latest changes
git pull origin akshat-dev

# Push your work
git add .
git commit -m "Akshat: implemented basic orchestrator logic"
git push origin akshat-dev
```

## General Git Guidelines for the Team
- **DO NOT** push directly to the `main` or `integration` branches. 
- Always work on your assigned branch (`shubham-dev`, `lavanya-dev`, `akshat-dev`).
- **The Integration Workflow:** 
  1. When your feature is complete, we will merge it into the **`integration`** branch first.
  2. The `integration` branch acts as a staging area where we test all agents together and resolve any merge conflicts.
  3. Once everything is working perfectly on `integration`, we will create a Pull Request to merge `integration` into `main` (production).
- If you need code from someone else's branch, ask them to push it, and then you can merge their branch into yours locally using `git merge origin/<their-branch-name>`.

---
*Project Repository: [Dynamic_CRM_Sales_Agents_Orchestration](https://github.com/Shubham231005/Dynamic_CRM_Sales_Agents_Orchestration)*
