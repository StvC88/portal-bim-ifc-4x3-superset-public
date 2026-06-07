FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 curl unzip \
    && rm -rf /var/lib/apt/lists/*

ARG IFCCONVERT_URL=https://s3.amazonaws.com/ifcopenshell-builds/IfcConvert-v0.8.6-938dda8-linux64.zip
RUN curl -L "$IFCCONVERT_URL" -o /tmp/IfcConvert.zip \
    && unzip /tmp/IfcConvert.zip -d /opt/ifcconvert \
    && find /opt/ifcconvert -type f -name IfcConvert -exec chmod +x {} \; \
    && ln -s "$(find /opt/ifcconvert -type f -name IfcConvert | head -n 1)" /usr/local/bin/IfcConvert \
    && rm /tmp/IfcConvert.zip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
