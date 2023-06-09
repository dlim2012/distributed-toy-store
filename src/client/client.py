#!usr/bin/python


import sys
import os

# import required packages
import threading

import requests
import random
import argparse
import time

from toynames import toy_names as product_choices

def parse():
    """
    This function will be used to parse input arguments to the main function
    Returns: arguments
    """
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('--front_host', type=str, default='127.0.0.1')
    parser.add_argument('--front_port', type=int, default=1110)
    parser.add_argument('--n_repeats', type=int, default=5)
    parser.add_argument('--n_threads', type=int, default=1)
    parser.add_argument('--p', type=float, default=0.5)
    parser.add_argument('--run_type', type=str, default='session_check')
    #(default: 'session_check', other choices: 'query', 'session')

    args = parser.parse_args()
    return args

# Parse arguments
args = parse()

# Use the os.getenv function to get values for REST_API_HOST and REST_API_PORT
REST_API_HOST = args.front_host
REST_API_PORT = args.front_port

# URL format and texts that will be used to make Query and Buy requests
URL = "http://{host}:{port}{path}"
QUERY_PATH = "/products/{product_name}"
BUY_PATH = "/orders"
CHECK_PATH = "/orders/{order_number}"

def query(session, product_name):
    # Make a Query request
    try:
        response = session.get(
            URL.format(
                host=REST_API_HOST,
                port=REST_API_PORT,
                path=QUERY_PATH.format(product_name=product_name)
            ),
            timeout=5,
            stream=False
        )
    except requests.exceptions.ReadTimeout:
        # Print error message for timeout exception
        print("The Query request failed. (Timeout)")
        return 'Timeout'

    # Print the results
    print("query(%s): [%d]" % (product_name, response.status_code), response.json())

    return response.json()

def buy(session, product_name, quantity):
    # Make a buy request
    try:
        response = session.post(
            URL.format(
                host=REST_API_HOST,
                port=REST_API_PORT,
                path=BUY_PATH
            ),
            json={"name": product_name, "quantity": quantity},
            timeout=5,
            stream=False
        )
    except requests.exceptions.ReadTimeout:
        # Print error message for timeout exception
        print("The Buy request failed. (Timeout)")
        return 'Timeout'

    # Print the results
    print("buy(%s, %d): [%d]" % (product_name, quantity, response.status_code), response.json())

    return response.json()

def check(session, order_number):
    # Make a check request
    try:
        response = session.post(
            URL.format(
                host=REST_API_HOST,
                port=REST_API_PORT,
                path=CHECK_PATH.format(order_number=order_number)
            ),
            timeout=5,
            stream=False
        )
    except requests.exceptions.ReadTimeout:
        # Print error message for timeout exception
        print("The Check request failed. (Timeout)")
        return 'Timeout'

    print("check(%d): [%d]" % (order_number, response.status_code), response.json())

    return response.json()


def run_sessions(n_repeats, p, thread_id=0, check_orders=True):
    """
    :param n_repeats: number of time to repeat sessions
    :param p: probability to send
    """
    run_type = {'query': 1, 'session': 2, 'session_check': 3}[args.run_type]
    start = time.time()
    purchases = []
    for _ in range(n_repeats):
        # Choose a product name and a quantity randomly
        product_name = random.choice(product_choices)
        quantity = 1

        # Initiate a new session
        session = requests.Session()

        # make a query call
        result = query(session, product_name)

        # Return if query failed with timeout or errors and if quantity is not bigger than 0
        if result == 'Timeout' or 'error' in result or result['data']['quantity'] < 1:
            # print(product_name, result)
            session.close()
            continue

        # Return with a probability of 1 - p
        if random.random() > p or run_type < 2:
            session.close()
            continue

        # Make a buy request
        result = buy(session, product_name, quantity)

        # Return if query faied with timeout or other errors
        if result == 'Timeout' or 'error' in result or result['data']['order_number'] < 0:
            session.close()
            continue


        # Get the order number from the buy request
        order_number = result['data']['order_number']

        # Return if order has failed
        if order_number < 0:
            session.close()
            continue

        # Add purchase information to 'purchases'
        purchases.append([order_number, product_name, 1])

        # Close the session
        session.close()

    if run_type == 3 and check_orders:
        session = requests.Session()
        for order_number, product_name, quantity in purchases:
            # Query purchase information
            data = check(session, order_number)['data']

            # Check that the information matches with the information from 'purchases'
            assert order_number == int(data['number'])
            assert product_name == data['name']
            assert quantity == int(data['quantity'])
        session.close()

    end = time.time()
    results[thread_id] = len(purchases), end - start


results = [None] * args.n_threads
def main():
    # Run sessions
    threads = []
    for i in range(args.n_threads):
        t = threading.Thread(target=run_sessions, args=(args.n_repeats, args.p, i, True))
        threads.append(t)

    sys.stdout = open(os.devnull, 'w')
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    sys.stdout = sys.__stdout__
    print(results)

    print("Average time: %.4f" % (sum([r[1] for r in results]) / args.n_threads))



if __name__ == '__main__':
    main()
