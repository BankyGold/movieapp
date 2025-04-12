# Set the python version as a build-time argument
ARG PYTHON_VERSION=3.12-slim-bullseye
FROM python:${PYTHON_VERSION}

# Create a virtual environment
RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

# Upgrade pip
RUN pip install --upgrade pip

# Set Python-related environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install OS dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    libjpeg-dev \
    libcairo2 \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create and set working directory
WORKDIR /code
COPY . /code/

# Install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

# Collect static files (assumes no DB dependency)
RUN python manage.py collectstatic --noinput

# Create runtime script
ARG PROJ_NAME="movieapp"
RUN printf "#!/bin/bash\n" > ./paracord_runner.sh && \
    printf "RUN_PORT=\"\${PORT:-8080}\"\n" >> ./paracord_runner.sh && \
    printf "echo \"Running migrations...\"\n" >> ./paracord_runner.sh && \
    printf "python manage.py migrate --noinput\n" >> ./paracord_runner.sh && \
    printf "echo \"Starting Gunicorn on port \$RUN_PORT...\"\n" >> ./paracord_runner.sh && \
    printf "gunicorn ${PROJ_NAME}.wsgi:application --bind \"0.0.0.0:\$RUN_PORT\" --workers 2 --timeout 90\n" >> ./paracord_runner.sh
RUN chmod +x paracord_runner.sh

# Clean up
RUN apt-get autoremove -y && apt-get clean && rm -rf /var/lib/apt/lists/*

CMD ["./paracord_runner.sh"]

