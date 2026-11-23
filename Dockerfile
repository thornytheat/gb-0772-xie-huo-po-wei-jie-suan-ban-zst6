FROM python:3.12-slim
WORKDIR /curb
COPY requirements.txt requirements-test.txt ./
RUN pip install --no-cache-dir -r requirements-test.txt
COPY . .
ENV CURB_DOCKET=/data/curb.sqlite3
EXPOSE 8000
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
