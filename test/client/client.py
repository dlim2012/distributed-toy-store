#!usr/bin/python

# import required packages
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
    parser.add_argument('--n_repeats', type=int, default=10)
    parser.add_argument('--p', type=float, default=0.2)


    args = parser.parse_args()
    return args

args = parse()

# Use the os.getenv function to get values for REST_API_HOST and REST_API_PORT
REST_API_HOST = args.front_host
REST_API_PORT = args.front_port

#REST_API_HOST = "52.23.247.147"
#REST_API_HOST = "ip-172-31-93-33.ec2.internal"
#REST_API_PORT = 1110

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


def run_sessions(n_repeats, p, check_orders=True):
    """
    :param n_repeats: number of time to repeat sessions
    :param p: probability to send
    """
    purchases = dict()
    for _ in range(n_repeats):
        # Choose a product name and a quantity randomly
        product_name = random.choice(product_choices)
        quantity = 1

        # Initiate a new session
        session = requests.Session()

        # make a query call
        result = query(session, product_name)
        print('query', (product_name,), result)

        # Return if query failed with timeout or errors and if quantity is not bigger than 0
        if result == 'Timeout' or 'error' in result or result['data']['quantity'] < 1:
            # print(product_name, result)
            session.close()
            continue

        # Return with a probability of 1 - p
        if random.random() > p:
            session.close()
            continue

        # Make a buy request
        result = buy(session, product_name, quantity)
        print('buy', (product_name, quantity), result)

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

        purchases[order_number] = (product_name, 1)

        # Close the session
        session.close()

    if check_orders:
        session = requests.Session()
        for order_number in purchases.keys():
            product_name, quantity = purchases[order_number]
            data = check(session, order_number)['data']

            assert order_number == int(data['number'])
            assert product_name == data['name']
            assert quantity == int(data['quantity'])
            print('check', (order_number, ), result)
        session.close()

    return len(purchases.keys())

def test_case():
    session = requests.Session()
    print("############################## TEST ###############################")
    product_name, quantity = "Tux", 1

    print("[Testcase 3] A query about the product \"Tux\" is handled using the catalog component.")
    query(session, product_name)
    print(); time.sleep(0.1)

    print("[Testcase 4] A query about the product \"Tux\" is handled using cache in the front-end component.")
    query(session, product_name)
    print(); time.sleep(0.1)

    print("[Testcase 5] A buy request for one \"Tux\" is successful. The information about \"Tux\" in front-end is invalidated.")
    order_number = buy(session, product_name, quantity)['data']['order_number']
    print(); time.sleep(0.1)

    print("[Testcase 6] A query about the product \"Tux\" is handled using the catalog component due to invalidate rpc call.")
    query(session, product_name)
    print(); time.sleep(0.1)

    print("[Testcase 7] A query about the previously made order is successful.")
    check(session, order_number)
    print(); time.sleep(0.1)

    print("[Testcase 8] During this buy request, the leader order component becomes inactive and a new leader selection is held. The purchase request is successfully handled by the new leader order component.")
    buy(session, product_name, quantity)
    print(); time.sleep(0.1)

    print("[Testcase 9] This request will make the quantity of \"Tux\" in catalog to be 0. Within one second the product \"Tux\" will be restocked. (It is set to one second only in the test.)")
    buy(session, product_name, quantity) # fail order 1
    print(); time.sleep(0.1)

    time.sleep(1)

    print("[Testcase 10] After the restock has happened, the quantity of \"Tux\" will be 100.")
    query(session, product_name)

    print("###################################################################")

# Choices of product names and quantities

def main():
    test_case()
    #run_sessions(args.n_repeats, args.p, check_orders=True)


if __name__ == '__main__':
    main()
