FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 3000
# Production WSGI server. Timetable generation can be slow on large datasets,
# so allow a generous worker timeout.
CMD ["gunicorn", "--workers", "3", "--timeout", "120", "--bind", "0.0.0.0:3000", "wsgi:app"]
