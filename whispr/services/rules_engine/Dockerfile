FROM python:3.11

WORKDIR /app

# Copy requirements and install dependencies
COPY services/rules_engine/requirements.txt .
RUN pip install -r requirements.txt

# Copy the rules engine code
COPY services/rules_engine/main.py .

# Copy the backend modules (database, llm, strategies, indicators, and all strategy modules)
COPY backend/database.py .
COPY backend/llm.py .
COPY backend/strategies.py .
COPY backend/indicators.py .
COPY backend/atr_strategy.py .
COPY backend/vomy_strategy.py .
COPY backend/four_h_po_dot_strategy.py .
COPY backend/conviction_arrow_strategy.py .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
