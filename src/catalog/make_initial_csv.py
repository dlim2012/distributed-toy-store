from csv_tools import write_csv
from toynames import toy_names
import random

def main():
    # Declare fields that will be place on the first row of the csv file to write
    fields = ["product_name", "price", "quantity"]

    random.seed(0)
    # Data to write
    # rows = [[toy_name, '%.2f' % random.uniform(10, 30), 100] for toy_name in set(toy_names)]
    rows = [[toy_name, '%.2f' % random.uniform(10, 30), 100000000] for toy_name in set(toy_names)]


    # Write data in a file
    file_name = "data/catalog.csv"
    write_csv(file_name, [fields] + rows)


if __name__ == '__main__':
    # Write a catalog file
    main()
