# Use an official Python Alpine Image
FROM python:3.12-alpine

LABEL maintainer="ian@icarey.net"

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /usr/src/app
COPY app.py /app
COPY lib /app/lib
COPY static /app/static
COPY templates /app/templates
COPY requirements.txt /app

RUN apk update && apk add --no-cache \
    build-base \
    git \
    file \
    ffmpeg \
    tzdata

# Set the timezone (example: America/New_York)
ENV TZ=America/New_York

# Clean up APK cache
RUN rm -rf /var/cache/apk/*

#Upgrade pip
RUN pip install --upgrade pip

# Install any needed packages specified in requirements.txt
RUN pip install --trusted-host pypi.python.org -r requirements.txt

# Run app.py when the container launches
CMD ["gunicorn", "-b", "0.0.0.0:9911", "app:app"]