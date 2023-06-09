#!/bin/bash

# Measures average time taken for each client to send $3 requests when 1 to 5 of client processes are initiated together.
# Arguments: $1(host ip address), $2(number of requests for each client), $3(p: probability of making purchase requests),
# $4(type of request: session_check, session, query, buy, check)
# ex. sh run_5_clients 128.119.243.1 100 0.5 session

if [ -z "$*" ];
then
    echo "No args";
    exit 0;
fi

rm results.txt
echo ""
i=1
echo "Initiating ${j} client process(es)."
while [ "$i" -le 5 ];
    do
    python3 client.py --front_host $1 --n_repeats $2 --p $3 --run_type $4 &
    i=$(( $i + 1 ))
done
wait
python3 calculate_average.py
