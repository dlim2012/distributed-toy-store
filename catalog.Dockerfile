FROM python:3.8-slim-buster

RUN pip install --upgrade pip

RUN pip install readerwriterlock==1.0.9 grpcio==1.44.0 grpcio-tools==1.44.0

WORKDIR /app

COPY src/catalog/catalog.py .

COPY src/catalog/catalog_pb2_grpc.py .

COPY src/catalog/catalog_pb2.py .

COPY src/catalog/csv_tools.py .

ENTRYPOINT ["python", "-u", "catalog.py"]
