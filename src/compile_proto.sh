python -m grpc_tools.protoc --proto_path=. ./catalog.proto --python_out=./ --grpc_python_out=./
python -m grpc_tools.protoc --proto_path=. ./order.proto --python_out=./ --grpc_python_out=./
python -m grpc_tools.protoc --proto_path=. ./front_end.proto --python_out=./ --grpc_python_out=./
python -m grpc_tools.protoc --proto_path=. ./order2.proto --python_out=./ --grpc_python_out=./

cp order_pb2.py ./front-end/order_pb2.py
cp order_pb2.py ./order/order_pb2.py
cp order_pb2_grpc.py ./front-end/order_pb2_grpc.py
cp order_pb2_grpc.py ./order/order_pb2_grpc.py

cp order2_pb2.py ./front-end/order2_pb2.py
cp order2_pb2.py ./order/order2_pb2.py
cp order2_pb2_grpc.py ./front-end/order2_pb2_grpc.py
cp order2_pb2_grpc.py ./order/order2_pb2_grpc.py

cp catalog_pb2.py ./front-end/catalog_pb2.py
cp catalog_pb2.py ./order/catalog_pb2.py
cp catalog_pb2.py ./catalog/catalog_pb2.py
cp catalog_pb2_grpc.py ./front-end/catalog_pb2_grpc.py
cp catalog_pb2_grpc.py ./order/catalog_pb2_grpc.py
cp catalog_pb2_grpc.py ./catalog/catalog_pb2_grpc.py

cp front_end_pb2.py ./front-end/front_end_pb2.py
cp front_end_pb2_grpc.py ./front-end/front_end_pb2_grpc.py
cp front_end_pb2.py ./catalog/front_end_pb2.py
cp front_end_pb2_grpc.py ./catalog/front_end_pb2_grpc.py

rm order_pb2.py
rm order_pb2_grpc.py
rm order2_pb2.py
rm order2_pb2_grpc.py
rm catalog_pb2.py
rm catalog_pb2_grpc.py
rm front_end_pb2.py
rm front_end_pb2_grpc.py