FROM python:3.9-slim

WORKDIR /app

# install runtime deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy your code and the serialized model
COPY worker.py model.joblib ./

# default command to launch Faust worker
CMD ["faust", "-A", "worker.app", "worker", "-l", "info"]
