# import required packages
import grpc
from concurrent import futures
import order_pb2, order_pb2_grpc, catalog_pb2, catalog_pb2_grpc, order2_pb2, order2_pb2_grpc
import threading
import os
from readerwriterlock import rwlock
from time import sleep

# import required files
from csv_tools import write_csv, read_log_file
import sys

# Use the os.getenv function to get values for
# ORDER_LOG_FILE, ORDER_PORT, CATALOG_HOST, CATALOG_PORT, and MAX_WORKERS
ORDER_LOG_FILE = os.getenv("ORDER_LOG_FILE", 'data/log1.csv')

# Order component ID of this instance
COMPONENT_ID = int(os.getenv("COMPONENT_ID", 1))

# Order components' addresses
ORDER_HOST_1 = os.getenv("ORDER_HOST_1", "127.0.0.1")
ORDER_PORT_1 = int(os.getenv("ORDER_PORT_1", 1121))
ORDER_HOST_2 = os.getenv("ORDER_HOST_2", "127.0.0.1")
ORDER_PORT_2 = int(os.getenv("ORDER_PORT_2", 1122))
ORDER_HOST_3 = os.getenv("ORDER_HOST_3", "127.0.0.1")
ORDER_PORT_3 = int(os.getenv("ORDER_PORT_3", 1123))

ORDER2_PORT_1 = int(os.getenv("ORDER2_PORT_1", 1124))
ORDER2_PORT_2 = int(os.getenv("ORDER2_PORT_1", 1125))
ORDER2_PORT_3 = int(os.getenv("ORDER2_PORT_1", 1126))

# Catalog component address
CATALOG_HOST = os.getenv("CATALOG_HOST", "127.0.0.1")
CATALOG_PORT = int(os.getenv("CATALOG_PORT", 1130))
MAX_WORKERS = int(os.getenv("MAX_WORKERS", 100))

# Component information
ORDER_HOSTS = [ORDER_HOST_1, ORDER_HOST_2, ORDER_HOST_3]
ORDER_PORTS = [ORDER_PORT_1, ORDER_PORT_2, ORDER_PORT_3]
ORDER2_PORTS = [ORDER2_PORT_1, ORDER2_PORT_2, ORDER2_PORT_3]
ORDER_PORT = ORDER_PORTS[COMPONENT_ID - 1]
ORDER2_PORT = ORDER2_PORTS[COMPONENT_ID - 1]

# Leader information
LEADER_ID = None
IS_LEADER = False

class CatalogStub(object):
    """
    A stub to make a Order call to Catalog Service
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

    def Order(self, product_name, quantity):
        """
        Make an Order rpc call to Catalog Service
        :param product_name: the name of the product to order
        :param quantity: the quantity to order
        :return: results from the reply
        """
        # Construct a message
        message = catalog_pb2.order(product_name=product_name,
                                    quantity=quantity)

        # Make the rpc call
        result = self.stub.Order(message, timeout=3)

        # Print the result
        print("[CatalogStub]", "Order(%s, %d):" % (product_name, quantity),
              "{'order_result': %d}" % result.order_result)

        # Return the result
        return result.order_result


class OrderStub(object):

    """
    A stub to make a Buy call to Order Service
    """
    def __init__(self, host, port, stub_id, servicer):
        """
        Initiate the stub
        :param host: server ip address
        :param port: server port number
        :param stub_id: the id of the order component that this stub is connecting to
        :param servicer: the OrderServicer instance that will use this stub
        """
        # Make a channel
        channel = grpc.insecure_channel('{}:{}'.format(host, port))

        # Initialize the stub
        self.stub = order_pb2_grpc.OrderStub(channel)

        # Save the stub id
        self.stub_id = stub_id

        # Save the OrderServicer instance
        self.servicer = servicer

    def Propagate(self, order_number, product_name, quantity):
        message = order_pb2.order_information(order_number=order_number, product_name=product_name, quantity=quantity)

        result = self.stub.Propagate(message)

        return result.ping_number


class OrderServicer(order_pb2_grpc.OrderServicer):
    """
    An OrderServicer object provides a Buy service through gRPC
    Use and modify data from self.catalog_file
    """
    def __init__(self, catalog_client, log_file):
        """
        Initialize an OrderServicer instance
        :param catalog_client: A stub to make Order rpc call to Catalog Service
        :param log_file: path to the file to write logs for successful orders
        """

        # Save the parameters
        self.catalog_client = catalog_client
        self.log_file = log_file

        # Get the log data and the last order number from log_file
        # Make a new file if the file doesn't exist
        self.log, self.order_number = read_log_file(log_file)
        self.write_number = self.order_number

        # Locks
        self.order_number_lock = threading.Lock()
        self.writer_number_lock = threading.Lock()
        log_lock = rwlock.RWLockFair()
        self.log_reader_lock = log_lock.gen_rlock()
        self.log_writer_lock = log_lock.gen_wlock()


        # Order stubs that will connect to other order component's servicers
        self.order_stubs = {i+1: OrderStub(ORDER_HOSTS[i], ORDER_PORTS[i], i+1, self) \
                            for i in range(3) if (i+1) != COMPONENT_ID}
        self.recovery_stubs = {i+1: RecoveryStub(ORDER_HOSTS[i], ORDER2_PORTS[i], i+1, self) \
                               for i in range(3) if (i+1) != COMPONENT_ID}

        # A threadpool that will be used to propagate order information to other order components
        self.threadpool = futures.ThreadPoolExecutor(2 * MAX_WORKERS)

        # Send requests for missing logs
        self.threadpool.submit(self._missing_logs)

        self.writer_thread = threading.Thread(target=self._write_log_in_file)
        self.writer_thread.start()


    def Buy(self, request, context):

        # If the quantity is invalid, -2 will be returned for the order number
        order_number = -2

        # Proceed the order only when the quantity is bigger than 0
        if request.quantity > 0:
            # Make an Order rpc call to Catalog and get the result
            order_result = self.catalog_client.Order(request.product_name, request.quantity)

            # If the order was successful
            if order_result == 1:

                # Get the order number and increase self.order_number
                self.order_number_lock.acquire()
                order_number = self.order_number
                self.order_number += 1
                self.order_number_lock.release()

                # Write the purchase information in memory
                self.log_writer_lock.acquire()
                self.log[order_number] = (request.product_name, request.quantity)
                self.log_writer_lock.release()

                # Propagate the purchase information to other components
                self.threadpool.submit(self._propagate, order_number, request.product_name, request.quantity)

            # If the order was not successful, return the order_result as the order_number
            else:
                order_number = order_result

        # Result to send for reply
        result = {"order_number": order_number}

        # Print the result
        print("[OrderSerivcer]", "Buy(%s, %d):" % (request.product_name, request.quantity), result)

        # Make a reply to the client
        return order_pb2.order_query(**result)

    def Check(self, request, context):
        """
        Handle Check rpc call made from the front-end component
        Using the received order number, reply with the purchase information.
        """

        # Get the purchase information using self.log_reader_lock
        self.log_reader_lock.acquire()
        if request.order_number not in self.log.keys():
            product_name, quantity = -1, -1
        else:
            product_name, quantity = self.log[request.order_number]
        self.log_reader_lock.release()

        result = {"product_name": product_name, "quantity": quantity}

        # Print the result
        print("[OrderSerivcer]", "Check(%d):" % (request.order_number), result)

        return order_pb2.order_details(**result)

    def Ping(self, request, context):
        """
        This function is used for leader selection
        """
        global LEADER_ID, IS_LEADER

        if request.ping_number == LEADER_ID:
            return order_pb2.ping(ping_number=0)

        # If the received ping_number is not 0, then the ping_number is the selected leader's component id
        if request.ping_number != 0:
            LEADER_ID = int(request.ping_number)
            if request.ping_number == COMPONENT_ID:
                IS_LEADER = True

            print("[OrderSerivcer] Leader selected. (LEADER_ID: %s, IS_LEADER: %s)" % (LEADER_ID, IS_LEADER))

        result = {"ping_number": 0}

        # Print the result
        #print("[OrderSerivcer]", "Ping(%d):" % (request.ping_number), result, 'LEADER_ID: %s, IS_LEADER: %s' % (LEADER_ID, IS_LEADER))

        return order_pb2.ping(**result)

    def Propagate(self, request, context):

        # Save the log information received from the leader component in memory.
        self.log_writer_lock.acquire()
        self.log[request.order_number] = (request.product_name, request.quantity)
        self.log_writer_lock.release()

        # Update the order number
        self.order_number_lock.acquire()
        self.order_number = request.order_number + 1
        self.order_number_lock.release()

        # Result will be an acknowledgement
        result = {"ping_number": 0}

        # Print out the result
        print("[OrderSerivcer]", "Propagate(%d, %s, %d):" % (request.order_number, request.product_name, request.quantity), result)

        return order_pb2.ping(**result)

    def _propagate(self, order_number, product_name, quantity, component_id=None):
        """
        This function will send propagate messages using threadpool to one or multiple other components
        """
        # If component id is given, propagate to the corresponding order component
        if component_id != None:
            self.threadpool.submit(self.__propagate, self.order_stubs[component_id], order_number, product_name, quantity)
            return

        # If component id is not given, propagate to all other order components
        for order_stub in self.order_stubs.values():
            self.threadpool.submit(self.__propagate, order_stub, order_number, product_name, quantity)

    def __propagate(self, order_stub, order_number, product_name, quantity):
        """
        This function will be executed in a threadpool to propagate log information to other order components
        :param i: the index of the order stub in self.order_stubs
        other parameters: log information
        """
        try:
            order_stub.Propagate(order_number, product_name, quantity)
        except:
            print('Propagate to component %d failed' % order_stub.stub_id)
        return

    def _missing_logs(self, order_numbers=None):
        """
        This function is called when the program is initiated.
        First, BackOnline rpc call is sent to one other component to get its current order number
        Second, missing order numbers from log is filled through RequestMissingLogs rpc call
        Third, repeat for all stubs
        """
        for recovery_stub in self.recovery_stubs.values():
            if order_numbers == None:
                try:
                    max_number = recovery_stub.BackOnline()
                    self.order_number_lock.acquire()
                    order_number = self.order_number
                    self.order_number_lock.release()
                    order_numbers = [i for i in range(order_number, max_number)]
                except:
                    continue
                self.__missing_logs(recovery_stub, order_numbers)
                order_numbers = None

    def __missing_logs(self, recovery_stub, order_numbers):
        """
        Try to get missing log information from other stubs
        """
        try:
            result = recovery_stub.RequestMissingLogs(order_numbers)
        except:
            pass

    def _write_log_in_file(self):
        """
        This function will be executed in a separate thread
        This thread will periodically write newly added logs in memory to disk
        """
        while True:
            # Sleep for one second before every write attempt
            sleep(1)

            # Append logs to a list before writing so that the file doesn't have to be opened several times
            to_write = []

            self.writer_number_lock.acquire()
            order_number = self.write_number
            self.writer_number_lock.release()
            while True:
                self.log_reader_lock.acquire()
                flag = order_number in self.log.keys()
                self.log_reader_lock.release()

                if flag:
                    # Append logs to write to a list
                    self.log_reader_lock.acquire()
                    product_name, quantity = self.log[order_number]
                    self.log_reader_lock.release()

                    to_write.append([order_number, product_name, quantity])

                    order_number += 1
                else:
                    # update write number
                    self.writer_number_lock.acquire()
                    self.write_number = order_number
                    self.writer_number_lock.release()

                    # Get current order number
                    self.order_number_lock.acquire()
                    current_order_number = self.order_number
                    self.order_number_lock.release()

                    if order_number < current_order_number:
                        # If there are missing numbers, gather the missing numbers
                        missing_numbers = []
                        for i in range(order_number, current_order_number):
                            self.log_reader_lock.acquire()
                            flag = i not in self.log.keys()
                            self.log_reader_lock.release()
                            if flag:
                                missing_numbers.append(i)

                        # Send a RequestMissingLogs rpc call to fill in the missing numbers
                        self._missing_logs(missing_numbers)
                    break

            # Write logs in the list
            write_csv(self.log_file, to_write, 'a')



class RecoveryStub(object):

    def __init__(self, host, port, stub_id, order_servicer):
        """
        Initiate the stub
        :param host: server ip address
        :param port: server port number
        :param stub_id: the id of the order component that this stub is connecting to
        """
        # Make a channel
        channel = grpc.insecure_channel('{}:{}'.format(host, port))

        # Initialize the stub
        self.stub = order2_pb2_grpc.RecoveryStub(channel)

        # Save the stub id
        self.stub_id = stub_id


        self.order_servicer = order_servicer

    def BackOnline(self):
        """
        Send a BackOnline rpc call and get the order number of other order components
        """
        result = self.stub.BackOnline(order2_pb2.ping2(ping_number=0))
        print('[RecoveryStub %d]' % self.stub_id, 'BackOnline:', result.ping_number)
        return result.ping_number

    def missing_number_iterator(self, order_numbers):
        """
        A function used to make an iterator for the RequestMissingLogs rpc call
        """
        for order_number in order_numbers:
            message = order2_pb2.missing_number(order_number=order_number, component_id=COMPONENT_ID)
            yield message

    def RequestMissingLogs(self, order_numbers):
        """
        A bidirection rpc used to fill in missing logs.
        Log information is received for each order number that is sent to other components
        """
        # Track the max order number received
        max_order_number = -1

        for response in self.stub.RequestMissingLogs(self.missing_number_iterator(order_numbers)):
            # Save received log information in memory
            self.order_servicer.log_writer_lock.acquire()
            self.order_servicer.log[response.order_number] = (response.product_name, response.quantity)
            self.order_servicer.log_writer_lock.release()

            print('[RecoveryStub %d]' % self.stub_id, 'RequestMissing(%d): (%d, %s, %d)' %
                  (response.order_number, response.order_number, response.product_name, response.quantity))

            max_order_number = max(max_order_number, response.order_number)

        # Update the order number
        self.order_servicer.order_number_lock.acquire()
        self.order_servicer.order_number = max(max_order_number + 1, self.order_servicer.order_number)
        self.order_servicer.order_number_lock.release()


class RecoveryServicer(order2_pb2_grpc.RecoveryServicer):

    def __init__(self, order_servicer):
        self.order_servicer = order_servicer

    def BackOnline(self, request, context):
        """
        When BackOnline rpc call is received, reply with the current order number of this order component
        """

        self.order_servicer.order_number_lock.acquire()
        max_number = self.order_servicer.order_number
        self.order_servicer.order_number_lock.release()

        message = order2_pb2.ping2(ping_number=max_number)
        print('[RecoveryServicer]', 'BackOnline')
        return message

    def RequestMissingLogs(self, request_iterator, context):
        """
        For each requested order_number, reply with the corresponding log information
        """

        for i, request in enumerate(request_iterator):

            # Get the log information
            self.order_servicer.log_reader_lock.acquire()
            product_name, quantity = self.order_servicer.log[request.order_number]
            self.order_servicer.log_reader_lock.release()

            message = order2_pb2.order_information2(
                order_number=request.order_number,
                product_name=product_name,
                quantity=quantity
            )

            print('[RecoveryServicer] RequestMissingLogs(%d): (%d, %s, %d)' %
                  (request.order_number, request.order_number, product_name, quantity))
            yield message

        print('[RecoveryServicer]', 'RequestMissingLogs')

def serve_order(order_log_file, max_workers):
    """
    Run the OrderServicer
    """

    # Make a server that consist of a dynamic thread pool using a built-in method
    # with limited maximum number of threads passed on using the argument "max_workers"
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=max_workers))

    # Register a ToyStore service to the thread pool
    # The object that will be passed for the items parameter is a dictionary that returns the number of stocks
    # and the price of the item entered as the key
    # items[itemName] = (number of stocks, price)
    order_pb2_grpc.add_OrderServicer_to_server(
        order_servicer,
        server)

    # Connect the server to a port number
    server.add_insecure_port(f'[::]:{ORDER_PORT}')

    # Start the server
    server.start()

    server.wait_for_termination()

def serve_recovery(order_servicer, max_workers):
    """
    Run the OrderServicer
    """

    # Make a server that consist of a dynamic thread pool using a built-in method
    # with limited maximum number of threads passed on using the argument "max_workers"
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=max_workers))

    # Register a ToyStore service to the thread pool
    # The object that will be passed for the items parameter is a dictionary that returns the number of stocks
    # and the price of the item entered as the key
    # items[itemName] = (number of stocks, price)
    order2_pb2_grpc.add_RecoveryServicer_to_server(
        RecoveryServicer(order_servicer),
        server)

    # Connect the server to a port number
    server.add_insecure_port(f'[::]:{ORDER2_PORT}')

    # Start the server
    server.start()

    server.wait_for_termination()



if __name__ == '__main__':

    sys.stdout = open(os.devnull, 'w')

    order_servicer = OrderServicer(CatalogStub(CATALOG_HOST, CATALOG_PORT), ORDER_LOG_FILE)

    # Call the serve function to start a new thread pool that runs OrderServicer
    t = threading.Thread(target=serve_recovery, args=(order_servicer, MAX_WORKERS))
    t.start()
    serve_order(order_servicer, MAX_WORKERS)
