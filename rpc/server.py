import threading
import socket
import argparse


def parse():
    """
    This function will parse the input arguments to the program
    :return: arguments
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=12345)
    parser.add_argument('--n_threads', type=int, default=10)

    args = parser.parse_args()
    return args


class QueueFromScratch():
    """
    A class for queue made from scratch
    """

    def __init__(self, capacity):
        """
        Initialize the class
        :param capacity: the maximum number of elements that the queue could hold
        """
        self.capacity = capacity
        self.array = [None] * capacity
        self.frontIndex = 0
        self.numberOfElements = 0

    def isEmpty(self):
        """
        Check if the queue is empty
        :return: True only if the number of elements inside the queue is zero
        """
        return self.numberOfElements == 0

    def isFull(self):
        """
        Check if the queue is full
        :return: True only if the queue is full
        """
        return self.numberOfElements == self.capacity

    def put(self, item):
        """
        Enqueue an item
        :param item: item that will be added
        :return: True when the item was added to the queue
        """
        if self.isFull():
            return 0

        insertIndex = (self.frontIndex + self.numberOfElements) % self.capacity
        self.array[insertIndex] = item
        self.numberOfElements += 1
        return 1

    def get(self):
        """
        Dequeue on item
        :return: the item that has been dequeued
        """
        if self.isEmpty():
            result = None
        else:
            result = self.array[self.frontIndex]

            self.frontIndex = (self.frontIndex + 1) % self.capacity
            self.numberOfElements -= 1
        return result

    def size(self):
        """
        Get the number of elements that are inside the queue
        :return:  the number of elements of the queue
        """
        return self.numberOfElements


"""
Class for our ThreadPool, takes a single positive integer as input and creates
a static threadpool with a fixed number of working threads.
"""


class ThreadPoolFromScratch():
    """
    A thread pool that is made using the "threading" package and the "QueueFromScratch" class
    """

    def __init__(self, numberOfThreads):
        """
        Initiate a static thread pool
        :param numberOfThreads: the number of threads that will be made for the thread pool
        """
        self.numberOfThreads = numberOfThreads

        # Capacity of the task Queue
        queueCapacity = numberOfThreads * 2

        # Declare a task queue with a capcity of QueueCapacity
        self.taskQueue = QueueFromScratch(queueCapacity)

        # A semaphore that will be used to prevent adding items when the queue is full
        self.semaphoreE = threading.Semaphore(queueCapacity)

        # A semaphore that will be used to prevent threads from using the taskQueue when the queue is empty
        self.semaphoreF = threading.Semaphore(0)

        # A semaphore that will be used to let only one thread to use the taskQueue
        self.semaphoreS = threading.Semaphore()


        # A list that will store threads
        self.workers = []

        # Creating Free threads for our static threadpool
        for i in range(numberOfThreads):
            worker = threading.Thread(target=self.getTask,
                                      args=(self.taskQueue, self.semaphoreE, self.semaphoreF, self.semaphoreS),
                                      daemon=True)
            self.workers.append(worker)

    def start(self):
        """
        Start all threads
        :return: None
        """
        for worker in self.workers:
            worker.start()

    def addToQueue(self, item):
        """
        Add a new task to our ThreadPool. A lock is used to synchronize "self.taskQueue".
        :param item: A tuple of the function and the arguments that consists a task
        :return: None
        """
        # Wait if there is no empty slots in self.taskQueue
        self.semaphoreE.acquire()

        # Acquire semaphoreS to synchronize self.taskQueue
        self.semaphoreS.acquire()

        # Put the given item to self.taskQueue
        self.taskQueue.put(item)

        # Release semaphoreS after using self.taskQueue
        self.semaphoreS.release()

        # Add one to semaphoreF._value since an element is added to self.taskQueue
        self.semaphoreF.release()


    def getTask(self, taskQueue, semaphoreE, semaphoreF, semaphoreS):
        """
        Get a new task from "self.taskQueue". A lock is used to synchronize "self.taskQueue".
        :param taskQueue: "self.taskQueue"
        :param semaphoreE: a semaphore that will be used to prevent adding items when the queue is full
        :param semaphoreF: a semaphore that will be used to prevent threads from using the taskQueue when the queue is empty
        :param semaphoreS: a semaphore that will be used to let only one thread to use the taskQueue
        :return: None
        """

        # Repeat until termination
        while True:
            # Get a task from "taskQueue"

            # Wait if there is no filled slots in self.taskQueue
            semaphoreF.acquire()

            # Acquire semaphoreS to synchronize self.taskQueue
            semaphoreS.acquire()

            # Get an item from self.taskQueue
            item = taskQueue.get()

            # Release semaphoreS after using self.taskQueue
            semaphoreS.release()

            # Add one to semaphoreE._value since an element is dequeued from self.taskQueue
            semaphoreE.release()



            if item == None:
                continue

            # If a task is found, run the task
            function, args = item
            function(*args)


class ServerUsingSocketConnections():
    """
    A server made from scratch using a "ThreadPoolFromScratch" instance and the "socket" package.
    """

    def __init__(self, numberOfThreads):
        """
        Initialize the server
        :param numberOfThreads: number of threads that will be used for the static thread pool
        """
        self.threadPool = ThreadPoolFromScratch(numberOfThreads)

        # A dictionary that will save the types of services
        self.services = dict()

        # Create a socket
        self.socket = socket.socket()

    def service(self, c):
        """
        Receive the first message and read the message to execute the corresponding method.
        If the message is not interpretable, send error message to the client and close the connection.
        :param c: the connected socket
        :return: None
        """

        try:
            # Set a timeout of 3 seconds
            c.settimeout(3)

            # Get the first message from the client and split it to words
            wordsInMessage = c.recv(1024).decode().split()

        except socket.timeout as err:
            # If timeout occurs, print out an error message and close the connection
            errorMessage = """
            Socket timeout occurred while trying to read the first message. This connection will be closed.
            """
            print(errorMessage)
            c.close()
            return

        # Error handling: send an error message to the client when the method name is not present in the right way.
        # Also, close the socket connection
        if len(wordsInMessage) == 0 or len(wordsInMessage[0]) == 0:
            replyMessage = "No method name specified. Ignoring this request."
            c.send(replyMessage.encode())
            c.close()
            return

        methodName, args = wordsInMessage[0], wordsInMessage[1:]

        # Error handling: send an error message to the client when the requested method is not served by the server
        # Also, close the socket connection
        if methodName not in self.services.keys():
            replyMessage = f"We don't have a method with name {methodName}. Ignoring this request."
            c.send(replyMessage.encode())
            c.close()
            return

        # Run the method with name of "methodName" with the given arguments
        self.services[methodName](c, args)

    def bind(self, host, portNumber):
        """
        Bind "self.socket" with the given host and portNumber
        :param host: server ip address
        :param port: server port number
        :return: None
        """

        self.socket.bind((host, portNumber))  # Bind to the port

    def addService(self, methodName, method):
        """
        Add a service to the instance
        :param methodName: the name of the method that will be served.
        :param method: the method that will be executed.
        :return:
        """
        # Throw a warning message if the methodName is already being used.
        if methodName in self.services.keys():
            warningMessage = f"""
                Warning: Service with name {methodName} already exists. 
                The service is substituted with the new method.
            """
            print(warningMessage)

        # Add the service to the instance
        self.services[methodName] = method

    def start(self):
        """
        Start the server
        :return: None
        """
        # Enable a server to accept connections
        self.socket.listen()

        # Start the threads in "self.threadPool"
        self.threadPool.start()

        # The main thread will be accepting requests.
        self.runUntilTermination()

    def runUntilTermination(self):
        """
        Accept requests and add them to the task queue.
        Run until termination.
        :return: None
        """
        while (True):
            # Accept a connection
            c, addr = self.socket.accept()

            # Add the connected socket to a queue so that other threads could handle it
            self.threadPool.addToQueue((self.service, (c,)))



class ToyStore():
    """
    Function to get inventory details in our Toy Store.
    """

    def __init__(self, toyStoreInventory):
        """
        Initialize an instance
        :param toyStoreInventory: A dictionary type that will store information about toys.
        """
        self.Inventory = toyStoreInventory

    def Query(self, c, args):
        """
        Send requested information to the client via the given socket connection
        :param c: socket that is connected to the client
        :param args: arguments
        :return:
        """
        # If itemName is not written in the received message, send '-1' to the client
        if len(args) == 0:
            replyMessage = '-1'
        # If there are more than one arguments, just use the first argument
        else:
            itemName = args[0]

            # If the toy is not present in our inventory the reply will be '-1'.
            if itemName not in self.Inventory:
                replyMessage = '-1'

            # If the toy is present but is out of stock the reply will be '0'.
            elif toyStoreInventory[itemName][0] == 0:
                replyMessage = '0'

            # If the item is in stock the reply will be the price of the toy.
            else:
                replyMessage = str(self.Inventory[itemName][1])

        # Send the reply to the client
        c.send(replyMessage.encode())

        # Close the socket connection
        c.close()


if __name__ == "__main__":
    args = parse()

    """
    Using a simple dictionary as the database for our toyStoreInventory,
    because of it's ease of access and also because of our small database.
    """
    toyStoreInventory = {
        "Whale": [500, 25.99],
        "Tux": [0, 19.99]
    }
    myToyStore = ToyStore(toyStoreInventory)

    # Make a server instance
    myServer = ServerUsingSocketConnections(numberOfThreads=args.n_threads)

    # Add a service to the server
    myServer.addService("Query", myToyStore.Query)

    # Bind a socket to a port
    myServer.bind(host=socket.gethostname(), portNumber=args.port)

    # Start the server and run until termination.
    myServer.start()
