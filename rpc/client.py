import socket
import argparse
import random


def parse():
    """
    This function will be used to parse input arguments to the main function
    Returns: arguments
    """
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('--host', type=str, default=socket.gethostname())
    parser.add_argument('--port', type=int, default=12345)
    parser.add_argument('--n_requests', type=int, default=10)

    args = parser.parse_args()
    return args

def query(host, port, itemName, verbose=False):
    """
    This function sends a "Query" call to the server.
    Args:
        host: server ip address
        port: server port number
        itemName: the name of the toy that will be queried
        verbose: results will be printed out only if verbose is True
    Returns: the response message from the server
    """

    # Make a socket and connect to the server
    s = socket.socket()
    s.connect((host, port))

    # Write the message that will be sent to the server
    # For the Query call, the format will be f"Query {itemName}" when itemName is the name of the toy
    message_to_sent = f"Query {itemName}"

    # Print a warning message if message_to_sent is too long.
    len = s.send(message_to_sent.encode())
    if len > 1024:
        warningMessage = f"""
            While performing "query": "Message too long(length: {len}), the first 1024 bytes have been transmitted."
            """
        print(warningMessage)

    try:
        # Wait for up to three seconds for a request by setting a timeout
        s.settimeout(3)

        # Get a response from the server
        received_message = s.recv(1024).decode("utf-8")

    # If timeout occurs, print an error message and close the socket conne
    except socket.timeout as err:
        errorMessage = """
            While performing "query": Socket timeout. The result has not came back. Closing the connection.
            """
        print(errorMessage)

    # Close the socket when done
    s.close()

    if verbose:
        if received_message == "":
            # Print out an error message if the socket connection got no reply
            print("\"{}\" has been sent, but no got no reply.".format(message_to_sent))
        else:
            # Print out the messages that were sent and received.
            print("Sent: {:<30s}Received: {:10s}".format(message_to_sent, received_message))

    return received_message


if __name__ == '__main__':
    # parse the input arguments to the main function
    args = parse()

    # server address (default: local host)
    host = args.host  # ex. "128.119.243.164"
    port = args.port  # port number of the server

    # Types of item names that will be queried.
    itemNames = ["Tux", "Whale", "Unicorn"]

    # Repeat sending a query request
    for i in range(args.n_requests):

        # Select a random item name from itemNames
        itemName = random.choice(itemNames)

        # Send a query request
        query(host, port, itemName, verbose=True)
