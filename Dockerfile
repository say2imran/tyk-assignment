FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY app crd_policies main.py /app/

ENV KUBECONFIG=$KUBECONFIG
ENV PORT=8080
EXPOSE ${PORT}

CMD ["python", "app/main.py", "--kubeconfig", "${KUBECONFIG}", "--address", ":${PORT}"]
