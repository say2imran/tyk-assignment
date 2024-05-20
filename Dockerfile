FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY crd_policies main.py /app/
COPY app /app/app/

ENV KUBECONFIG=/app/kubeconfig/client.config
ENV PORT=8080
EXPOSE ${PORT}

CMD ["python", "main.py", "--kubeconfig", "${KUBECONFIG}", "--address", ":${PORT}"]