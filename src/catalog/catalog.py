# Import required packages
import threading
import grpc
from concurrent import futures
from readerwriterlock import rwlock
import time
import os, sys
import copy

# Import other files
import catalog_pb2 as pb2
import catalog_pb2_grpc as pb2_grpc
import front_end_pb2, front_end_pb2_grpc
from csv_tools import read_catalog, write_csv

# Get the value for CATALOG_FILE, CATALOG_PORT, and MAX_WORKERS
# through the os.getenv function.
FRONT_HOST = os.getenv("FRONT_HOST", "127.0.0.1")
FRONT_PORT = int(os.getenv("FRONT_PORT", 1111))
CATALOG_FILE = os.getenv("CATALOG_FILE", "data/catalog.csv")
CATALOG_PORT = int(os.getenv("CATALOG_PORT", 1130))
MAX_WORKERS = int(os.getenv("MAX_WORKERS", 100))

# The time interval between restock attempts
RESTOCK_INTERVAL = int(os.getenv("RESTOCK_INTERVAL", 10))


class CatalogServicer(pb2_grpc.CatalogServicer):
    """
    A CatalogServicer object provides Query and Order services through gRPC
    Use and modify data from self.catalog_file
    """

    def __init__(self, catalog_file):
        """
        :param catalog_file: path to the catalog file to read and write data
        """

        # Path to the catalog file
        self.catalog_file = catalog_file

        # Read the catalog file
        self.fields, self.catalog = read_catalog(self.catalog_file)

        # A dictionary that stores product names as keys and give the index of the product in self.catalog
        self.retriever = dict()
        for i, row in enumerate(self.catalog):
            self.retriever[row[0]] = i

        # A readwritelock used for the synchronization of the product catalog
        catalog_lock = rwlock.RWLockFair()
        self.reader_lock = catalog_lock.gen_rlock()
        self.writer_lock = catalog_lock.gen_wlock()

        # A boolean that is used to check whether self.catalog has been modified
        self.catalog_modified = False
        self.catalog_modified_lock = threading.Lock()

        # A thread periodically writes the data in self.catalog to the catalog_file in disk
        self.writer_thread = threading.Thread(target=self.write_catalog_file)
        self.writer_thread.start()

        # A thread periodically restock toys that are out of stock
        self.restock_thread = threading.Thread(target=self.restock_out_of_stocks)
        self.restock_thread.start()

        # A stub that will send invalidate requests to the front-end component
        self.front_stub = FrontStub(FRONT_HOST, FRONT_PORT)

        #
        self.threadpool = futures.ThreadPoolExecutor(MAX_WORKERS)

    def Query(self, request, context):
        """
        Query rpc call
        """

        # If the product_name is not found, return -1, -1 to the client
        if request.product_name not in self.retriever.keys():
            price, quantity = '-1', -1
        else:
            index = self.retriever[request.product_name]

            # Acquire a reader lock for self.catalog
            self.reader_lock.acquire(blocking=True, timeout=1)

            # Read required data from self.catalog
            price, quantity = self.catalog[index][1:3]

            # Release the reader lock after reading from self.catalog
            self.reader_lock.release()

        # Send back the response to the client
        result = {'price': price, 'quantity': quantity}

        # Print Results
        print("[CatalogServicer]", "Query(%s):" % request.product_name, result)

        # Reply to the client
        return pb2.query_response(**result)

    def Order(self, request, context):

        # Read relevant data from self.catalog and modify it if needed
        if request.product_name not in self.retriever.keys():
            # 1) If the product name is not found
            order_result = -3
            print("(Buy Failed) %s: invalid item" % request.product_name)
        elif request.quantity < 1:
            # 2) If the quantity is not bigger than 0
            order_result = -2
            print("(Buy Failed) %d: invalid quantity" % request.quantity)
        else:
            # Get the index of the product for self.catalog
            index = self.retriever[request.product_name]

            # Acquire a writer lock for self.catalog
            self.writer_lock.acquire(blocking=True, timeout=1)
            quantity = self.catalog[index][2]

            # 3) When there is enough quantity: buy successful
            if quantity >= request.quantity:

                # Reduce quantity in self.catalog
                self.catalog[index][2] -= request.quantity

                # Release ther writer lock
                self.writer_lock.release()

                # Order result: 1 (successful)
                order_result = 1

                # Change self.catalog_modified to True so that another thread could change the catalog file in disk
                self.catalog_modified_lock.acquire()
                self.catalog_modified = True
                self.catalog_modified_lock.release()

                # Print the buy result
                print("(Buy Successful) %s: (before: %d) -> (after: %d)" % (
                request.product_name, quantity, quantity - request.quantity))

            # 4) Not enough quantity: but failed
            else:

                # Release the writer lock
                self.writer_lock.release()

                # Order result: -1 (not enough stock)
                order_result = -1

                # Print the buy result
                print("(Buy Failed) %s: (remaining: %d) < (requested: %d)" % (
                request.product_name, quantity, request.quantity))

        # Send back the response to the client
        result = {'order_result': order_result}

        # Print the results
        print("[CatalogServicer]", "Order(%s, %d): {'order_result': %d}"
              % (request.product_name, request.quantity, order_result))

        # Send an invalidate request to the front-end component since the catalog information has changed
        self.invalidate(request.product_name)

        return pb2.order_result(**result)

    def write_catalog_file(self, interval=1):
        """
        One thread will write data from self.catalog to disk periodically
        only if self.catalog has been modified since last write
        :param interval: seconds to wait between each attempt to write
        """
        while True:
            # Sleep for 'interval' seconds to attempt writing periodically
            time.sleep(interval)

            # Write only if self.catalog has been modified
            if self.catalog_modified:
                # Copy data in self.catalog using a reader lock
                self.reader_lock.acquire(blocking=True, timeout=5)
                to_write = copy.deepcopy(self.catalog)
                self.reader_lock.release()

                # Write the copied data to disk
                write_csv(self.catalog_file, [self.fields] + to_write)

                # Change the self.catalog_modified to False
                self.catalog_modified_lock.acquire()
                self.catalog_modified = False
                self.catalog_modified_lock.release()

    def restock_out_of_stocks(self):
        """
        Periodically check the catalog and restock out-of-stock items to 100.
        """

        while True:
            # Restock periodically (default: 10 seconds)
            time.sleep(RESTOCK_INTERVAL)

            # Gather information about products that are out of stock.
            items_to_restock_idx = []
            self.reader_lock.acquire()
            for i, row in enumerate(self.catalog):
                if row[2] == 0:
                    items_to_restock_idx.append(i)
            self.reader_lock.release()

            if len(items_to_restock_idx) > 0:
                for idx in items_to_restock_idx:
                    # Modify the quantity of out-of-stock products
                    self.writer_lock.acquire()
                    print('Restocking', self.catalog[idx], end=" -> ")
                    self.catalog[idx][2] = 100
                    print(self.catalog[idx])
                    self.writer_lock.release()

                    # Send an invalidate request to the front-end component since the catalog information has changed
                    self.invalidate(self.catalog[idx][0])

            # Leave a mark so that the writer thread could know that the catalog information has changed
            self.catalog_modified_lock.acquire()
            self.catalog_modified = True
            self.catalog_modified_lock.release()

    def invalidate(self, product_name):
        # Send a in validation request using a threadpool
        self.threadpool.submit(self.front_stub.Invalidate, product_name)


class FrontStub(object):
    def __init__(self, host, port):
        """
        Initiate the stub
        :param host: server ip address
        :param port: server port number
        """
        # Make a channel
        channel = grpc.insecure_channel('{}:{}'.format(host, port))

        # Initialize the stub
        self.stub = front_end_pb2_grpc.FrontStub(channel)

    def Invalidate(self, product_name):
        """
        Send a invalidate request to the front-end component
        """
        # Make the message to send
        message = front_end_pb2.product_front(product_name=product_name)

        # Send the request
        result = self.stub.Invalidate(message, timeout=1)

        # Print out the result
        print("[FrontStub]", "Invalidate(%s)" % product_name, result)

        return


def serve(catalog_file, port, max_workers):
    # Make a server that consist of a dynamic thread pool using a built-in method
    # with limited maximum number of threads passed on using the argument "max_workers"
    print(port)
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=max_workers))

    # Register CatalogServicer to the thread pool
    pb2_grpc.add_CatalogServicer_to_server(
        CatalogServicer(catalog_file=catalog_file),
        server)

    # Connect the server to a port number
    server.add_insecure_port(f'[::]:{port}')

    # Start the server
    server.start()

    # Block current thread until the server stops
    server.wait_for_termination()


if __name__ == '__main__':

    # disable print
    sys.stdout = open(os.devnull, 'w')

    # Start the server
    serve(CATALOG_FILE, CATALOG_PORT, MAX_WORKERS)
