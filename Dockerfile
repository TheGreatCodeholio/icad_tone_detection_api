# Use an official Python runtime as a parent image
FROM python:3.11

LABEL maintainer="ian@icarey.net"

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /usr/src/app
COPY app.py /app
COPY lib /app/lib
COPY static /app/static
COPY templates /app/templates
COPY requirements.txt /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

#install ffmpeg
RUN apt update && apt install -y ffmpeg

# Run app.py when the container launches
CMD ["gunicorn", "-b", "0.0.0.0:9911", "app:app"]