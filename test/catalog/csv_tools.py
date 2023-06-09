import csv

def write_csv(file_name, rows):
    """
    Write a csv file
    :param file_name: path of the file
    :param rows: each row be written in a line
    """
    with open(file_name, 'w') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerows(rows)


def read_catalog(file_name):
    """
    Read catalog from a csv file
    :param file_name: path of the file
    :return:
        fields: Column information from the csv file
        rows: Each row will contain data for each product
    """
    # Read each row from the file
    rows = []
    with open(file_name, 'r') as csvfile:
        csvreader = csv.reader(csvfile)
        for row in csvreader:
            rows.append(row)

    # The first row is the field variable that contains the column information
    field, rows = rows[0], rows[1:]

    # Change the data type of the third column into int
    # This is the quantity of the product
    for row in rows:
        row[2] = int(row[2])

    # Return results
    return field, rows