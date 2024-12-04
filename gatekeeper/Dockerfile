# Use a lightweight Python image
FROM python:3.9-slim

# Set the working directory in the container
COPY instance_details.json /app/instance_details.json
WORKDIR /app

# Copy application files to the container
COPY . /app

# Install required Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port the application will run on
EXPOSE 8000

# Command to run the application
CMD ["python", "gatekeeper.py"]

