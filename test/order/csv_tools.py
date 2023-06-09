import csv
import os
import shutil
from datetime import datetime


def write_csv(file_name, rows, mode='a'):
    """
    Write a csv file or add to a csv file.
    :param file_name: path of the file
    :param rows: each row be written in a line
    :param mode: mode to open file ('w': write, 'a': add)
    """
    with open(file_name, mode) as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerows(rows)


def make_new_order_log_file(file_name):
    """
    Make a new log file
    :param file_name: path to the file
    """
    # Write the fields to the log file
    fields = ['Order number', 'Product name', 'Quantity']
    write_csv(file_name, [fields], 'w')


def read_log_file(file_name):
    """
    Get the next order number to use
    Order numbers: unique, incremental order, starting from 0
    :param file_name: path of the file
    :return: the next order number to use
    """

    if not os.path.exists(file_name):
        # If the file doesn't exist, create a file and return 0
        make_new_order_log_file(file_name)
        return dict(), 0

    with open(file_name, 'r') as csvfile:

        try:
            # Skip the header
            next(csvfile)
        except:
            # The log file is empty
            # Make a new order log if the log file is invalid
            make_new_order_log_file(file_name)
            return dict(), 0

        # Go to the last line
        log = dict()
        max_order_number = -1

        reader = csv.reader(csvfile, delimiter=',')
        for line in reader:
            if len(line) != 3:
                make_new_order_log_file(file_name)
                return dict(), 0
            log[int(line[0])] = (line[1], int(line[2]))
            max_order_number = max(max_order_number, int(line[0]))

    # Return the next order number
    return log, max_order_number + 1