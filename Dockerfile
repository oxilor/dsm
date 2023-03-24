FROM python:3.11-alpine

RUN pip install --no-cache-dir pipenv

COPY . .

RUN pipenv install --deploy --ignore-pipfile

ENTRYPOINT ["pipenv", "run", "python", "main.py"]
