FROM python:3.11

WORKDIR /app

# Copy requirements and install dependencies
COPY services/rules_engine/requirements.txt .
RUN pip install -r requirements.txt

# Copy the rules engine code
COPY services/rules_engine/main.py .

# Copy the backend modules (database, rules, llm)
COPY backend/database.py .
COPY backend/rules.py .
COPY backend/llm.py .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"] 