# Nagarikta OCR

A microservice-based OCR project for Nepali citizenship cards, supporting both **front** (numbers) and **back** (text blocks) using PaddleOCR and Tesseract fallback.

---

## Features

- **Front side:** Optimized for Devanagari numbers (PaddleOCR primary, Tesseract fallback)  
- **Back side:** Optimized for mixed Nepali/English text blocks  
- Automatic engine selection with fallback if OCR fails  
- REST API endpoints for OCR and health checks  
- Dockerized for easy setup and isolation  

---

## Prerequisites

- Docker & Docker Compose installed
- At least 12 GB free disk space
- Python 3.10 (if running outside Docker)

---

## Quick Start (Docker)

1. Clone the repository:
2. git clone https://github.com/kiranneupane11/Nagarikta-OCR.git
3. cd Nagarikta-OCR
   
### Build and start services: 
- docker-compose up --build

This will start the following services:

- ocr_service → REST API for OCR processing on port 9000
- llm_service → Text extraction / post-processing on port 8001
- preprocess_service → Preprocessing service on port 8000
- ollama → Local LLM backend

Verify services:

curl http://localhost:9000/health
curl http://localhost:8001/health
curl http://localhost:8000/health

All should return:

{"status":"running","service":"ocr_service"}

## Running OCR
POST a request to the OCR API:

curl -X POST "http://localhost:8000/preprocess" -F "file=@/path/to/your/image.png"
