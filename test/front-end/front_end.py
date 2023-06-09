#!/usr/bin/env python3

# Import required packages
import grpc
from grpc._channel import _InactiveRpcError
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
import threading
import json
import re
import os
from concurrent import futures
import sys
import time

# Import required files
import catalog_pb2 as catalog_pb2
import catalog_pb2_grpc as catalog_pb2_grpc
import order_pb2 as order_pb2
import order_pb2_grpc as order_pb2_grpc
import front_end_pb2 as pb2
import front_end_pb2_grpc as pb2_grpc

# Get information about the port number to use
REST_API_PORT = os.getenv("RESTFUL_API_PORT", 1110)
FRONT_PORT = int(os.getenv("FRONT_PORT", 1111))

# Get information about order component addresses
ORDER_HOST_1 = os.getenv("ORDER_HOST_1", "127.0.0.1")
ORDER_PORT_1 = int(os.getenv("ORDER_PORT_1", 1121))
ORDER_HOST_2 = os.getenv("ORDER_HOST_2", "127.0.0.1")
ORDER_PORT_2 = int(os.getenv("ORDER_PORT_2", 1122))
ORDER_HOST_3 = os.getenv("ORDER_HOST_3", "127.0.0.1")
ORDER_PORT_3 = int(os.getenv("ORDER_PORT_3", 1123))

# Get information about catalog component addresses
CATALOG_HOST = os.getenv("CATALOG_HOST", "127.0.0.1")
CATALOG_PORT = int(os.getenv("CATALOG_PORT", 1130))

# Max workers that will be used to handle requests
MAX_WORKERS = int(os.getenv("MAX_WORKERS", 100))

# A global variable that will save the ID of the order leader component
ORDER_LEADER_ID = None
ORDER_SELECTION_IN_PROCESS = False
ORDER_SELECTION_IN_PROCESS_LOCK = threading.Lock()

class CatalogStub(object):
    """
    A stub to make a Query call to Catalog Service
    """
    def __init__(self, host, port):
        """
        Initiate the stub
        :param host: server ip address
        :param port: server port number
        """
        # Make a channel
        channel = grpc.insecure_channel('{}:{}'.format(host, port))

        # Initialize the stub
        self.stub = catalog_pb2_grpc.CatalogStub(channel)

    def Query(self, product_name):
        """
        Make a Query rpc call to Catalog Service
        :param product_name: the product name to query
        :return: results from the reply
        """
        # Construct a message
        message = catalog_pb2.product(product_name=product_name)

        # Make the rpc call
        result = self.stub.Query(message, timeout=3)

        # Print the result
        print("[CatalogStub]", "Query(%s):" % product_name, "{'price': %s, 'quantity': %d)" %(result.price, result.quantity))

        # Return the result
        return result.price, result.quantity


class OrderStub(object):
    """
    A stub to make a Buy call to Order Service
    """
    def __init__(self, host, port, stub_id):
        """
        Initiate the stub
        :param host: server ip address
        :param port: server port number
        :param stub_id: The id of the order component that this stub will connect to
        """
        # Make a channel
        channel = grpc.insecure_channel('{}:{}'.format(host, port))

        # Initialize the stub
        self.stub = order_pb2_grpc.OrderStub(channel)

        # Save the stub id
        self.stub_id = stub_id

    def Buy(self, product_name, quantity):
        """
        Make a Buy rpc call to Order Service
        :param product_name: the name of the product
        :param quantity: the quantity to buy
        :return: results from the reply
        """
        # Construct a message
        message = order_pb2.order_details(product_name=product_name, quantity=quantity)

        # Make the rpc call
        result = self.stub.Buy(message, timeout=1)

        # Print the result
        print("[OrderStub %d]" % self.stub_id, "Buy(%s, %d):" % (product_name, quantity), "{\'order_number\': %d}" % result.order_number)

        # Return the result
        return result.order_number

    def Check(self, order_number):
        """
        Make a Check rpc call to Order Service to get order details
        :param order_number: order number
        :return: results from the reply
        """
        # Construct a message
        message = order_pb2.order_query(order_number=order_number)

        # Make the rpc call
        result = self.stub.Check(message, timeout=3)

        # Print the result
        print("[OrderStub %d]" % self.stub_id, "Check(%s, %d):"
              % (result.product_name, result.quantity), "{\'order_number\': %d}" % order_number)

        # Return the result
        return result.product_name, result.quantity

    def Ping(self, ping_number):

        # Construct a message
        message = order_pb2.ping(ping_number=ping_number)

        # Make the rpc call
        result = self.stub.Ping(message, timeout=1)

        # Print the result
        #print("\t[OrderStub %d]" % self.stub_id,"Ping(%d):" % ping_number, "{\'ping_number\': %d}" % result.ping_number)

        return result.ping_number


class FrontServicer(pb2_grpc.FrontServicer):
    def Invalidate(self, request, context):
        """
        This servicer is made to receive invalidate requests from the catalog component
        """

        # Always return 0 as a response
        result = {'response': 0}

        # Print out the result
        print("[FrontServicer]", "Invalidate(%s):" % request.product_name, result)

        try:
            # Remove the relevant information from cache if available
            cache.pop(request.product_name)
            print('[Cache] pop(%s)' % request.product_name)
        except KeyError:
            pass

        return pb2.invalidation_response(**result)


class NotFlask():
    """
    A class made to make use of decorators just as in the Flask package
    Also, the parsing of the path of each request is done by this class
    """
    def __init__(self):
        """
        Initiate the instance
        """

        # Patterns of the path will be saved in this list
        self.routes = []

    @staticmethod
    def build_route_pattern(route):
        # Build a route pattern from a string
        route_regex = re.sub(r'(<\w+>)', r'(?P\1.+)', route)
        return re.compile("^{}$".format(route_regex))

    def route(self, route_str):
        # Define a route decorator
        def decorator(f):
            route_pattern = self.build_route_pattern(route_str)
            self.routes.append((route_pattern, f))

            return f

        return decorator

    def get_route_match(self, path):
        # If the last character of path is '/', remove the last character
        if path[-1] == '/':
            path = path[:-1]

        # Find pattern match in self.routes
        # If found, return the parsed results
        for route_pattern, view_function in self.routes:
            m = route_pattern.match(path)
            if m:
                return m.groupdict(), view_function

        # If not found return None
        return None

    def serve(self, handler):
        # Find if there is a pattern match
        route_match = self.get_route_match(handler.path)
        if route_match:
            # If there is a match, call the corresponding function
            kwargs, view_function = route_match
            return view_function(handler, **kwargs)
        else:
            # If there is no match, raise an error
            raise ValueError('Route "{}"" has not been registered'.format(handler.path))


# Make a NotFlask class
app = NotFlask()


@app.route("/products/<product_name>")
def query(handler, product_name):
    """
    This function handles Query requests from client
    It uses the route decorator of a NotFlask instance
    :param handler: the request handler that has information about parsed HTTP request
    :param product_name: the name of the product to query
    :return: status code and paylaod
    """

    try:
        # First try to get the required information from cache
        price, quantity = cache[product_name]
        print('[Cache] query request(%s): {price: %s, quantity: %d}' % (product_name, price, quantity))
    except:
        try:
            # Make a stub call
            price, quantity = catalog_stub.Query(product_name)
        except:
            # If error, send a "internal server error" reply
            return handler.error(500, "internal server error")

        if quantity == -1:
            # When the product name is not found in the Catalog Service, return "product not found" error
            return handler.error(404, "product not found")

        cache[product_name] = (price, quantity)

    # Make a payload if there was no error
    data = {
        "name": product_name,
        "price": price,
        "quantity": quantity
    }
    payload = json.dumps({"data": data})

    # Return a status code of 200 and the payload
    return 200, payload


@app.route("/orders")
def buy(handler):
    """
    This function handles Buy requests from client
    It uses the route decorator of a NotFlask instance
    :param handler: the request handler that has information about parsed HTTP request
    :return: status code and paylaod
    """

    # Send an error reply if 'Content-Type' is not given as a header
    if 'Content-Type' not in handler.headers.keys():
        return handler.error(400, "(Missing header) \"Content-Type: application/json\" header required")

    # Send an error reply if 'Content-Type' is not 'application/json'
    if handler.headers['Content-Type'] != "application/json":
        return handler.error(415, "(Wrong Content-Type) \"Content-Type: application/json\" header required")

    # Send an error reply if 'Content-Length' is not given as a header
    if 'Content-Length' not in handler.headers.keys():
        return handler.error(411, "Content-Length header required")

    try:
        # Read the json payload
        data = json.loads(handler.rfile.read(int(handler.headers['Content-Length'])))
    except:
        # Send an error reply if the json payload is not interpretable
        return handler.error(400, "invalid json file")

    # Send an error reply if the json payload doesn't contain required information
    if "name" not in data.keys() or "quantity" not in data.keys():
        return handler.error(400, "invalid json file (required keys: name, quantity)")

    if data["quantity"] < 1:
        # Send an error reply for invalid quantity
        return handler.error(400, "invalid quantity.")

    global ORDER_LEADER_ID
    while True:
        try:
            # Make a Buy rpc call to the Order service
            order_number = order_stubs[ORDER_LEADER_ID-1].Buy(data["name"], data["quantity"])
            break
        except _InactiveRpcError as e:
            # If the order leader component is inactive, perform leader selection again
            orderstub_leader_selection(order_stubs)
        except SystemExit:
            # If there are no order component that is active, stop the program
            sys.exit(1)
        except Exception as e:
            print(e)
            # Send an error reply if the Buy rpc call was not successful
            return handler.error(500, "internal server error")

    if order_number < 0:
        if order_number == -3:
            # Send an error reply if the product was not found in the catalog
            return handler.error(404, "product not found")
        elif order_number == -2:
            # Send an error reply for invalid quantity
            return handler.error(400, "invalid quantity.")
        # when quantity is not enough: return order_number -1

    # If there was no error, make a payload for reply
    payload = json.dumps({"data": {"order_number": order_number}})

    # Return a status code of 200 and the payload
    return 200, payload


@app.route("/orders/<order_number>")
def check(handler, order_number):
    global ORDER_LEADER_ID
    while True:
        try:
            # Make a stub call
            product_name, quantity = order_stubs[ORDER_LEADER_ID-1].Check(int(order_number))

            if quantity == -1:
                # When the product name is not found in the Catalog Service, return "product not found" error
                return handler.error(404, "product not found")
            break
        except _InactiveRpcError as e:
            # If the order leader component is inactive, perform leader selection again
            orderstub_leader_selection(order_stubs)
        except SystemExit:
            # If there are no order component that is active, stop the program
            sys.exit(1)
        except:
            # If error, send a "internal server error" reply
            return handler.error(500, "internal server error")


    # Make a payload if there was no error
    data = {
        "number": order_number,
        "name": product_name,
        "quantity": quantity
    }
    payload = json.dumps({"data": data})

    # Return a status code of 200 and the payload
    return 200, payload


class RequestHandler(BaseHTTPRequestHandler):
    # Change the protocol version to enable handling multiple requests in one session
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        """
        Disabled log message
        """
        return

    def send_error(self, code, message=None, explain=None):
        """Send and log an error reply.
        Arguments are
        * code:    an HTTP error code
                   3 digits
        * message: a simple optional 1 line reason phrase.
                   *( HTAB / SP / VCHAR / %x80-FF )
                   defaults to short entry matching the response code
        * explain: a detailed message defaults to the long entry
                   matching the response code.
        """
        # Send a reply with error code and message
        self.reply(*self.error(int(code), message))

    def error(self, code, message):
        """
        Make error message
        :param code: an HTTP error code
        :param message: error message
        :return: HTTP error code and a json that will be sent as a payload
        """
        return code, json.dumps({"error": {"code": code, "message": message}})

    def reply(self, status_code, payload):
        """
        Make the reply message with a json payload and send the reply to the client
        :param status_code: HTTP status code
        :param payload: payload to attach (format: json)
        """
        # Send the HTTP status
        self.send_response(status_code)

        # Add headers for the json payload
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()

        # Add the payload
        self.wfile.write(payload.encode('utf-8'))


    def do_GET(self):
        """
        Handle the GET request after parsing the requested HTTP message
        """

        try:
            # Use the app object to process the request
            status_code, payload = app.serve(self)
        except ValueError:
            # A value error will occur when the service type is not implemented
            # Make an error payload
            status_code, payload = self.error(501, "service not implemented")
        except SystemExit:
            sys.exit(1)
        except:
            # For other errors such as when other components are down
            # make an error payload with "internal server error"
            status_code, payload = self.error(500, "internal server error")

        # Send the reply
        self.reply(status_code, payload)


    def do_POST(self):
        """
        Handle the POST request after parsing the requested HTTP message
        """

        try:
            # Use the app object to process the request
            status_code, payload = app.serve(self)
        except ValueError:
            # A value error will occur when the service type is not implemented
            # Make an error payload
            status_code, payload = self.error(501, "service not implemented")
        except SystemExit:
            sys.exit(1)
        except:
            # For other errors such as when other components are down
            # make an error payload with "internal server error"
            status_code, payload = self.error(500, "internal server error")

        # Send the reply
        self.reply(status_code, payload)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """
    A threaded HTTP server that use thread-per-session to handle requests
    """
    pass


def orderstub_leader_selection(order_stubs):
    """
    This functino will select the leader of the order components
    """

    global ORDER_LEADER_ID, ORDER_SELECTION_IN_PROCESS, ORDER_SELECTION_IN_PROCESS_LOCK

    print('Choosing the leader of OrderStub...')
    ORDER_SELECTION_IN_PROCESS_LOCK.acquire()
    if ORDER_LEADER_ID is not None:
        try:
            is_alive = (order_stubs[ORDER_LEADER_ID-1].Ping(ORDER_LEADER_ID) == 0)
            if is_alive:
                ORDER_SELECTION_IN_PROCESS_LOCK.release()
                return
        except:
            pass

    for i in range(len(order_stubs)):
        order_stub = order_stubs[i]
        try:
            # Check if the order component is alive and select the component as the leader
            # The order component with the lowest id will be prioritized
            is_alive = (order_stub.Ping(0) == 0)
            ORDER_LEADER_ID = i + 1
            print('\tLeader Selected:', ORDER_LEADER_ID)

            # If the leader is selected, make all components know the result
            if is_alive:
                for j in range(i, len(order_stubs)):
                    try:
                        order_stubs[j].Ping(ORDER_LEADER_ID)
                    except:
                        print('\tOrder stub %d not responding' % (j+1))
                        pass
            ORDER_SELECTION_IN_PROCESS_LOCK.release()
            return 1
        except:
            print('\tPing to Order stub %d failed' % (i+1))

    ORDER_SELECTION_IN_PROCESS_LOCK.release()
    # If no order components are active, exit the program
    print("\tNo order component is active... exiting program...")
    sys.exit(1)

def check_alive(order_stubs):
    while True:
        order_stub = order_stubs[ORDER_LEADER_ID-1]
        is_alive = False
        try:
            is_alive = (order_stub.Ping(ORDER_LEADER_ID) == 0)
        except:
            pass
        if not is_alive:
            orderstub_leader_selection(order_stubs)
        time.sleep(1)

def serve_grpc(port, max_workers):
    # Make a server that consist of a dynamic thread pool using a built-in method
    # with limited maximum number of threads passed on using the argument "max_workers"
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=max_workers))

    # Register CatalogServicer to the thread pool
    pb2_grpc.add_FrontServicer_to_server(
         FrontServicer(),
        server)

    # Connect the server to a port number
    server.add_insecure_port(f'[::]:{port}')

    # Start the server
    server.start()

    # Block current thread until the server stops
    server.wait_for_termination()


def main():
    # Run the FrontServicer using a threadpool from a separate thread
    t = threading.Thread(target=serve_grpc, args=(FRONT_PORT, MAX_WORKERS))
    t.start()

    t = threading.Thread(target=check_alive, args=(order_stubs,))
    t.start()

    # Start a threaded HTTP server in local host
    server = ThreadedHTTPServer(('0.0.0.0', REST_API_PORT), RequestHandler)

    # Set server timeout as 10
    server.timeout = 10

    # Run the server
    server.serve_forever()


# Make a catalog stub and a order stub to send rpc calls to Catalog Service and Order Service respectively.
catalog_stub = CatalogStub(CATALOG_HOST, CATALOG_PORT)
order_stubs = [
    OrderStub(ORDER_HOST_1, ORDER_PORT_1, 1),
    OrderStub(ORDER_HOST_2, ORDER_PORT_2, 2),
    OrderStub(ORDER_HOST_3, ORDER_PORT_3, 3)
]

# A cache that will be used to save product information received from the catalog component
cache = dict()


if __name__ == "__main__":
    print("############################## TEST ###############################")
    print("[Testcase 2] Leader Selection")

    # Select a leader order component
    orderstub_leader_selection(order_stubs)
    print("###################################################################")


    # Run the Server
    main()
