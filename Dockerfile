FROM python:3.12-alpine

WORKDIR /app

COPY ./app .

RUN pip install -r requirements.txt

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]