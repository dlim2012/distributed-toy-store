"""
This file made to calculate average time among multiple client processes in each experiment.
"""

with open("results.txt", "r") as f:
    results = f.read()
    results = [float(i) for i in results.split() if len(i) > 0]
average = sum(results) / len(results)
print("Average: %.4f" % round(average, 4), results)
