FROM python:3.8-slim-buster

RUN pip install --upgrade pip

RUN pip install httpserver==1.1.0 grpcio==1.44.0 grpcio-tools==1.44.0

WORKDIR /app

COPY src/front-end/front_end.py .

COPY src/front-end/catalog_pb2_grpc.py .

COPY src/front-end/catalog_pb2.py .

COPY src/front-end/order_pb2_grpc.py .

COPY src/front-end/order_pb2.py .

ENTRYPOINT ["python", "-u", "front_end.py"]
