# FROM python:3.12.2
FROM public.ecr.aws/docker/library/python:3.12.2-slim-bullseye
ENV PYTHONBUFFERED=1
ENV PORT=8080
WORKDIR /app
COPY . /app/
RUN apt-get update && apt-get install -y ffmpeg
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy and set entrypoint
COPY entry.sh /app/entry.sh
RUN chmod +x /app/entry.sh

# Run app with gunicorn command
# CMD ["gunicorn", "conf.wsgi:application", "--bind", "0.0.0.0:8080"]

EXPOSE ${PORT}
ENTRYPOINT ["/app/entry.sh"]