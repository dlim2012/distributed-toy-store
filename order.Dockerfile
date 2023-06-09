FROM python:3.8-slim-buster

RUN pip install --upgrade pip

RUN pip install grpcio==1.44.0 grpcio-tools==1.44.0

WORKDIR /app

COPY src/order/order.py .

COPY src/order/catalog_pb2_grpc.py .

COPY src/order/catalog_pb2.py .

COPY src/order/order_pb2_grpc.py .

COPY src/order/order_pb2.py .

COPY src/order/csv_tools.py .

ENTRYPOINT ["python", "-u", "order.py"]
