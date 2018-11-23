#!/usr/bin/python
# -*- coding: utf-8 -*-

import jinja2
from urllib.parse import urlencode
from urllib.request import Request, urlopen

templateLoader = jinja2.FileSystemLoader(searchpath="./")
templateEnv = jinja2.Environment(loader=templateLoader)
TEMPLATE_FILE = "template.txt"
template = templateEnv.get_template(TEMPLATE_FILE)

URL = 'https://httpbin.org/post' # Set destination URL here


import csv
with open('data.csv', newline='') as csvfile:
    reader = csv.DictReader(csvfile)
    rows = list(reader)
    for index, row in enumerate(rows):
        tel = row['Gsm nummer']
        matchRowNumber = int(row['Match'])
        matchRow = rows[matchRowNumber]
        if(index != int(matchRow['Match'])):
            print(index, " ", matchRowNumber, " index does not match")
            
        message = template.render(user=row, match=matchRow)
        post_fields = {'message': "test"}     # Set POST fields here

        request = Request(URL, urlencode(post_fields).encode())
        json = urlopen(request).read().decode()
        print(json)
        print(message)