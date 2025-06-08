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

# Install os dependencies for our mini vm
RUN apt-get update && apt-get install -y \
    # for postgres
    libpq-dev \
    # for Pillow
    build-essential \

    libjpeg-dev \
    # for CairoSVG
    libcairo2 \
    # other
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create the mini vm's code directory
RUN mkdir -p /code

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
    printf "RUN_PORT=\"\${PORT:-8000}\"\n\n" >> ./paracord_runner.sh && \
    printf "python manage.py migrate --no-input\n" >> ./paracord_runner.sh && \
    printf "gunicorn ${PROJ_NAME}.wsgi:application --bind \"[::]:\$RUN_PORT\"\n" >> ./paracord_runner.sh

RUN echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser(email='banky@gmail.com', password='7904', first_name='Admin', last_name='User') if not User.objects.filter(email='banky@gmail.com').exists() else None" | python manage.py shell

RUN chmod +x paracord_runner.sh

# Clean up apt cache to reduce image size
RUN apt-get remove --purge -y \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

CMD ["./paracord_runner.sh"]

