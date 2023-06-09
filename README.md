# Distributed Toy-Store Service
This repository implements a microservices-based containerized toy-store service.
The connection between users and the frontend uses REST APIs which are handled by an HTTP Server and a Flask-like implementation.
There are three microservices: frontend, order, and catalog, and they communicate using RPC calls.
Features of caching and crash failure data recovery are added.

# How to run the codes

## 1. Catalog components

### Example in bash
```commandline
cd src/catalog
python3 catalog.py
```
### Environment Variables (catalog.py)
```
FRONT_HOST: name or ip address of the front-end component (default: '127.0.0.1')
FRONT_PORT: port number of the front-end component (default: 1111)
CATALOG_FILE: path to the catalog file (default: "data/catalog.csv")
CATALOG_PORT: port number of the catalog component (default: 1130)
```
### To initialize catalog file in disk
```
cd src/catalog
python3 make_initial_csv.py
```

## 2. Order components
### Example in bash 
```bash
# First component
cd toy-store/order
COMPONENT_ID=1 ORDER_LOG_FILE=data/log1.csv python3 order.py
```
```bash
# Second component
cd toy-store/order
COMPONENT_ID=2 ORDER_LOG_FILE=data/log2.csv python3 order.py
```
```bash
# Third component
cd toy-store/order
COMPONENT_ID=3 ORDER_LOG_FILE=data/log3.csv python3 order.py
```
### Environment Variables
```
COMPONENT_ID: The component ID of the instance. (default: 1)
ORDER_LOG_FILE: path to the log file (default: "data/log1.csv")

ORDER_HOST_1: name or ip address of the first order component (default: '127.0.0.1')
ORDER_PORT_1: port number of the order service of the first order component (default: 1121)
ORDER_HOST_2: name or ip address of the second order component (default: '127.0.0.1')
ORDER_PORT_2: port number of the order service of the second order component (default: 1122)
ORDER_HOST_3: name or ip address of the third order component (default: '127.0.0.1')
ORDER_PORT_3: port number of the order service of the third order component (default: 1123)

ORDER2_PORT_1: port number of the recovery service of the first order component (default: 1124)
ORDER2_PORT_2: port number of the recovery service of the second order component (default: 1125)
ORDER2_PORT_3: port number of the recovery service of the thrid order component (default: 1126)

CATALOG_HOST: name or ip address of the catalog component (default: '127.0.0.1')
CATALOG_PORT: port number of the catalog component (default: 1130)
```


## 3. Front-end components
### Example in bash
```commandline
cd src/front-end
python3 front_end.py
```
### Environment Variables
```
REST_API_PORT: port number of the restful API of the front-end component (default: 1110)
FRONT_PORT: port number of the front servicer of the front-end component (default: 1111)

ORDER_HOST_1: name or ip address of the first order component (default: '127.0.0.1')
ORDER_PORT_1: port number of the order service of the first order component (default: 1121)
ORDER_HOST_2: name or ip address of the second order component (default: '127.0.0.1')
ORDER_PORT_2: port number of the order service of the second order component (default: 1122)
ORDER_HOST_3: name or ip address of the third order component (default: '127.0.0.1')
ORDER_PORT_3: port number of the order service of the third order component (default: 1123)

CATALOG_HOST: name or ip address of the catalog component (default: '127.0.0.1')
CATALOG_PORT: port number of the catalog component (default: 1130)
```


## 4. Client components
### Example in bash
```commandline
cd src/client
python3 client.py
```
### Arguments
```
--front_host: name or ip address of the front-end component (default: '127.0.0.1')
--front_port: port number of the restful API of the front-end component (default: 1110)
--n_repeats: number of sessions to run(default: 10)
--n_threads: number of clients to run (each client runs in a different thread)
--p: probability to send purchase requests after query requests if not out-of-stock. (default: 0.5)
--run_type: session types to run (default: 'session_check', other choices: 'query', 'session')
```

