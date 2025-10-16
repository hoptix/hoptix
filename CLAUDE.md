# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Hoptix is a drive-thru analytics platform for restaurants (specifically Dairy Queen). It processes audio recordings from drive-thru interactions, transcribes them, analyzes transactions for upselling/upsizing/add-on opportunities, and provides analytics dashboards to track performance.

## Architecture

This is a microservices architecture with 4 main services:

### 1. **backend/** - Analytics & Processing Backend (Flask + Python)
Main analytics backend that processes transactions and provides analytics APIs.

**Key responsibilities:**
- Processes audio from Google Drive
- Orchestrates full pipeline: audio → transcription → transaction splitting → grading
- Stores analytics data in Supabase
- Serves analytics APIs for frontend consumption

**Core pipeline flow** (backend/pipeline/full_pipeline.py):
1. Fetch audio from location + date (services/gdrive.py or services/media.py)
2. Transcribe audio to text (services/transcribe.py using OpenAI)
3. Split transcript into transactions (services/transactions.py)
4. Grade transactions for upsell/upsize/add-on opportunities (services/grader.py)
5. Store results in Supabase database (services/database.py)

**Key services:**
- `services/analytics.py` - Analytics calculations (upsell/upsize/addon metrics)
- `services/grader.py` - Grades transactions using OpenAI against menu JSON files
- `services/transcribe.py` - Audio transcription via OpenAI Whisper
- `services/gdrive.py` - Google Drive integration for audio files
- `services/database.py` - Supabase database wrapper

**Grading system:**
The grader uses extensive prompts (config.py Prompts class) and menu JSON files (prompts/ directory in hoptix-flask) to evaluate:
- Upsell opportunities (burger → meal)
- Upsize opportunities (medium → large)
- Add-on opportunities (extra toppings)
- Uses Item ID format: `[Item ID]_[Size ID]` (e.g., "16_2" for Medium Misty Freeze)

### 2. **hoptix-flask/** - Legacy Processing Service (Flask + Python)
Original processing service with WAV splitting, importing, and video processing capabilities. Some functionality overlaps with backend/.

**Key components:**
- `services/wav_splitter.py` - Splits multi-hour audio files into manageable chunks
- `services/import_service.py` - Imports audio from various sources
- `services/processing_service.py` - Main processing orchestration
- `services/item_lookup_service.py` - Menu item lookup and validation
- `services/voice_diarization.py` - Speaker identification (currently commented out in pipeline)
- `prompts/` - JSON files with menu items, meals, upselling rules, etc.

### 3. **frontend/** - Analytics Dashboard (Next.js 15 + TypeScript)
React-based dashboard for viewing analytics and transaction data.

**Tech stack:**
- Next.js 15 (App Router)
- TypeScript
- Tailwind CSS + shadcn/ui components
- Recharts for data visualization
- TanStack Query for data fetching

**Main routes:**
- `/dashboard` - Main analytics dashboard
- `/analytics` - Detailed analytics views
- `/runs` - Processing run history
- `/items` - Item-specific analytics
- `/reports` - Generated reports
- `/videos` - Video footage review
- `/samples` - Sample data

### 4. **auth-service/** - Authentication Service (Go + Python wrapper)
Supabase Auth wrapper with additional security middleware.

**Note:** Has both Go binary (`auth-service`) and Python wrapper (`main.py`). The Go service provides JWT validation, RBAC, OAuth, admin features. See auth-service/README for full feature list.

## Database

Uses **Supabase** (PostgreSQL) as primary database. Key tables/views:
- `orgs` - Organizations (restaurant chains)
- `locations` - Restaurant locations
- `runs` - Processing run metadata
- `transactions` - Individual drive-thru transactions
- `grades` - Graded transaction analysis
- `graded_rows_filtered` - View for filtered/complete transaction grades

All services connect via Supabase client using `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`.

## Environment Setup

### Backend (Python services)
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Required `.env` variables (see backend/.env or config.py):
- `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`
- `AWS_REGION`, `RAW_BUCKET`, `DERIV_BUCKET` (S3 storage)
- `SQS_QUEUE_URL` (message queue for processing)
- `OPENAI_API_KEY`
- `ASR_MODEL`, `STEP1_MODEL`, `STEP2_MODEL` (OpenAI models)

### Frontend (Next.js)
```bash
cd frontend
npm install
```

Required `.env`:
- `NEXT_PUBLIC_BACKEND_URL` (points to backend Flask service)
- `NEXT_PUBLIC_AUTH_URL` (points to auth-service)

### Auth Service
See auth-service/Makefile for setup. Python version requires:
```bash
cd auth-service
pip install -r requirements.txt
```

Required `.env`:
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`

## Common Commands

### Backend
```bash
# Run backend server
cd backend
python app.py  # Runs on port 8000

# Run tests
cd backend
pytest tests/

# Process a specific location and date
# (Use the full_pipeline function from pipeline/full_pipeline.py)
```

### Frontend
```bash
cd frontend
npm run dev        # Development server (port 3000)
npm run build      # Production build
npm run start      # Production server
npm run lint       # ESLint
npm run type-check # TypeScript checking
```

### Auth Service
```bash
cd auth-service

# Python tests
make test                # Run all tests
make test-connectivity   # Quick connectivity tests
make test-predeploy      # Pre-deployment tests
```

### Hoptix-Flask
```bash
cd hoptix-flask
python app.py  # Run the Flask service
```

## Key Concepts

### Transaction Grading
Transactions are graded on three dimensions:
1. **Upselling** - Did operator offer to upgrade items to meals/combos?
2. **Upsizing** - Did operator offer to upsize to large?
3. **Add-ons** - Did operator offer additional toppings?

For each dimension, we track:
- Opportunities (how many chances existed)
- Offers (how many were actually offered)
- Success (how many were accepted)

### Item ID Format
All menu items use `[Item ID]_[Size ID]` format:
- Size IDs: 0=default, 1=small/kid's, 2=medium/regular, 3=large
- Example: "16_2" = Medium Misty Freeze
- Reference: hoptix-flask/prompts/items.json and meals.json

### Worker-based Analytics
Analytics can be filtered by `worker_id` to track individual employee performance. See backend/services/analytics.py for worker-specific queries.

### Run-based Processing
Each processing job creates a `run_id` that ties together:
- The audio file processed
- All transactions extracted
- All grades generated
- Analytics reports

## Testing

### Backend Tests
```bash
cd backend
pytest tests/test_analytics.py      # Analytics calculations
pytest tests/test_media_service.py  # Media processing
pytest tests/test_gdrive_audio_by_date.py  # Google Drive integration
```

### Auth Service Tests
```bash
cd auth-service
make test-connectivity    # Fast connectivity tests
make test                 # Full test suite (60+ tests)
```

## Important Files

- `backend/config.py` - All configuration, environment variables, and grading prompts (500+ lines of detailed grading instructions)
- `backend/pipeline/full_pipeline.py` - Main processing pipeline orchestration
- `hoptix-flask/prompts/*.json` - Menu definitions and upselling rules
- `frontend/package.json` - Frontend dependencies and scripts
- `auth-service/Makefile` - Auth service build and test commands

## Data Flow

1. Audio files stored in Google Drive or AWS S3
2. Backend fetches audio for specific location + date
3. Audio transcribed via OpenAI Whisper
4. Transcript split into individual transactions
5. Each transaction graded against menu JSON using OpenAI
6. Results stored in Supabase
7. Frontend queries Supabase via backend APIs
8. Analytics displayed in dashboard

## Notes

- The `hoptix-flask/` service has some overlapping functionality with `backend/` - check both when adding processing features
- Menu items and grading rules are defined in JSON files in `hoptix-flask/prompts/`
- Voice diarization code exists but is currently commented out in the pipeline
- SQS queue is configured but check if worker implementation is active
- Some Python cache files (__pycache__) are tracked in git - consider adding to .gitignore
