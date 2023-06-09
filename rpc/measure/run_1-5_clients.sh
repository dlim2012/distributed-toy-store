#!/bin/bash

# Measures average time taken for each client to send $3 requests when 1 to 5 of client processes are initiated together.
# Arguments: $1(host ip address), $2(port number), $3(number of requests for each client), $4(type of request: query or buy)
# ex. sh run_1-5_clients 128.119.243.1 2345 100 query

if [ -z "$*" ];
then
    echo "No args";
    exit 0;
fi

j=1
while [ "$j" -le 5 ];
    do
    rm results.txt
    echo ""
    i=1
    echo "Initiating ${j} client process(es)."
    while [ "$i" -le "$j" ];
        do
        python3 client.py --host $1 --port $2 --n_requests $3 &
        i=$(( $i + 1 ))
    done
    wait
    python3 calculate_average.py
    j=$(( $j + 1 ))
done
