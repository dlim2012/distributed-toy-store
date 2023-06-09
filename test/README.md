# Output file
The output is shown in 'Test Output file.pdf'.

# Setups for testing

### Initial catalog
The initial quantity of the product "Tux" is set to 3 in the catalog file in disk.

### Simulating crash
Order componenets are modified to fail while handling the third purchase request.

### Other adjustments
The time interval between restock attempts are reduced to 0.5 second.

The client will send pre-defined requests.

### Printed Messages:
All messages that are printed using ‘[‘ and ‘]’ follows the following format.
*	[\<Class name of stub instance\>] \<request name\>(\<parameters\>): \<request result\>
*	If a class name ends with ‘Stub’, then the instance is the client side of the RPC call.
*	If a class name ends with ‘Servicer’, then the instance is the server side of the RPC call.

Ping RPC calls are not printed out as they are used periodically.

Some other printed out messages:
* Whether Purchase was successful in the catalog component.
* Leader selection
* Restocking

# Test steps

## Step 1: Run the catalog component

```bash
cd ./catalog
python3 catalog.py
```

(A test about restocking will be held on testcase 9.)

## Step 2: Run the order component 1


```bash
cd ./order
COMPONENT_ID=1 ORDER_LOG_FILE=data/log1.csv python3 order.py
```

## Step 3: Run the order component 2


```bash
cd ./order
COMPONENT_ID=2 ORDER_LOG_FILE=data/log2.csv python3 order.py
```
A BackOnline RPC call is made from order component 2 to order component 1.

## Step 4: Run the order component 3

```bash
cd ./order
COMPONENT_ID=3 ORDER_LOG_FILE=data/log3.csv python3 order.py
```
Testcase 1. The log file for order component 3 is missing two latest logs. The <ins>missing logs will be filled</ins> by making RequestMissingLogs to other components.


## Step 5: Run the front-end component


```bash
cd ./front-end
python3 front_end.py
```
Testcase 2. A <ins>leader selection</ins> for order components will be performed.

## Step 6: Run the client

```bash
cd ./client
python3 client.py
```

Testcase 3. query("Tux"): A query about a product will be replied by <ins>using a Query RPC call</ins> to the catalog component.

Testcase 4. query("Tux"): A query about a product will be replied by <ins>using cache</ins>.

Testcase 5. buy("Tux", 1): A purchase request will be successful and return order number 3. An <ins>Invalidate RPC call</ins> will remove the product information from cache in the front-end component.

Testcase 6. query("Tux"): A query about a product will be replied by <ins>using a Query RPC call</ins> to the catalog component.

Testcase 7. check(3): A <ins>query about log information</ins> for the previous purchase request will be successful.

Testcase 8. buy("Tux", 1): During this purchase request, the first order component will be down. <ins>Another leader selection</ins> for order components will be performed. Eventually, order component 2 will handle the purchase request.

Testcase 9. buy("Tux", 1): This purchase request will make the stock of "Tux" to be 0. Within about one second, the quantity for this product will be <ins>restocked</ins> to 100 and an <ins>Invalidate message</ins> will be sent.

Testcase 10. query("Tux"): This request will be made 1 second after the previous buy request. The product "Tux" will <ins>have quantity of 100 due to restock</ins>. Also, the query will be handled <ins>using a Query RPC call</ins> in the front-end component.

## Step 7: Restart the order component 1
```bash
cd ./order
COMPONENT_ID=1 ORDER_LOG_FILE=data/log1.csv python3 order.py
```

Testcase 11. Upon recovery, the first order component will <ins>recover the log information</ins> that has been missed.
