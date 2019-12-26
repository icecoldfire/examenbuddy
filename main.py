# python3
#!/usr/bin/python
# -*- coding: utf-8 -*-
import csv
import random
from fuzzywuzzy import fuzz
import jinja2
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from time import sleep

FILE = "data.csv"
BUDDIES = []

templateLoader = jinja2.FileSystemLoader(searchpath="./")
templateEnv = jinja2.Environment(loader=templateLoader)
TEMPLATE_FILE = "template.txt"
FEEDBACK_FILE = "template-feedback.txt"
CONFIRM_FILE = "template-confirm.txt"
template = templateEnv.get_template(TEMPLATE_FILE)
feedback = templateEnv.get_template(FEEDBACK_FILE)
confirm = templateEnv.get_template(CONFIRM_FILE)

URL = 'http://192.168.1.3:8080/v1/sms/' # Set destination URL here

random.seed(4)

# Fields this year:
###########
# Timestamp
# Naam
# Gsmnummer
# Hoekanjouwbuddyjecontacteren
# Schaarsteenpapierofbladsteenschaar
# District
# Schooltype
#    Middelbaar, Hoger beroeps onderwijs, Hoge school, Universiteit
# Waarstudeerje
# Zitjeopkot

class Buddy:
    def __init__(self, buddyDict):
        self.props = {}
        self.taken = False
        self.buddy = None

        for key in buddyDict:
            self.props[self._cleanup(key)] = buddyDict[key]

        self.props["Hoekanjouwbuddyjecontacteren"] = sorted(self.props["Hoekanjouwbuddyjecontacteren"].split(";"))

    def findMatch(self):
        candidates = []

        for buddy in BUDDIES:
            if (buddy.taken is True):
                continue

            if (buddy == self):
                continue

            # Middelbaar begint vroeger, dus die matchen we apart
            if self.props["Schooltype"] == "Middelbaar" and buddy.props["Schooltype"] != "Middelbaar" or \
               self.props["Schooltype"] != "Middelbaar" and buddy.props["Schooltype"] == "Middelbaar":
                continue

            # Fuzzy matching op district, we willen enkel mensen van andere districten.
            if fuzz.ratio(self.props["District"], buddy.props["District"]) > 80:
                continue

            # Kandidaten worden gesorteerd op aantal overeenkomstige communicatie kanalen
            coms = self.props["Hoekanjouwbuddyjecontacteren"]
            buddycoms = buddy.props["Hoekanjouwbuddyjecontacteren"]

            common = list(set(coms).intersection(buddycoms))
            buddyExtra = [item for item in buddycoms if item not in common]
            
            score = (len(common) - len(buddyExtra)) / len(coms)
            candidates.append((score, buddy))

        # Sort based on score (better = better match between communication channels)
        candidates = sorted(candidates, key=lambda tup: tup[0], reverse=True)


        if (len(candidates) > 0):
            filterScore = candidates[0][0]

            # Filter away the non-optimal candidates
            candidates = list(filter(lambda score: score[0] >= filterScore, candidates))
            random.shuffle(candidates)

            return candidates[0][1]
        else:
            return None
        
    def _cleanup(self, string):
        '''Used to clean up space and ascii bloated csv keys, retains alphanumeric characters'''

        newstr = ""
        for char in string:
            if (char.isalnum()):
                newstr += char

        if (newstr == ""):
            return "randkey" + str(random.randint(10000000,     99999999))

        return newstr

    def __str__(self):
        return self.props["Naam"] + "(" + str(self.props["Gsmnummer"]) + ")"

    def __repr__(self):
        return self.props["Naam"] + "(" + str(self.props["Gsmnummer"]) + ")"


def matchmaker(iteration=0):
    print("Matchmaker iteration", iteration)

    random.shuffle(BUDDIES)
    nomatch = 0
    nomatches = []

    matches = []
    for buddy in BUDDIES:
        if (buddy.taken is True):
            continue

        match = buddy.findMatch()

        if match is not None:
            buddy.buddy = match
            buddy.taken = True

            match.buddy = buddy
            match.taken = True

            matches.append((buddy, match))
        else:
            nomatch += 1
            nomatches.append(buddy)

        if nomatch > 2:
            return matchmaker(iteration + 1)

    for sad in nomatches:
        print("No match found for", sad)

    return matches

def printStatistics():
    print("Aantal snapchatbuddies:", len(BUDDIES))
    middelbaar = 0
    notmiddelbaar = 0
    districten = []

    for buddy in BUDDIES:
        if buddy.props["Schooltype"] == "Middelbaar":
            middelbaar += 1
        else:
            notmiddelbaar += 1

        add = True
        for district in districten:
            if fuzz.ratio(buddy.props["District"], district) > 80:
                add = False
                break

        if add is True:
            districten.append(buddy.props["District"])

    districten = list(sorted(districten))

    print("Aantal middelbaar:", middelbaar)
    print("Aantal niet middelbaar:", notmiddelbaar)
    print("Alle districten (fuzzy matching):", ', '.join(districten))
    print("")
    
def send_match_message(user, match):
    phone = user.props['Gsmnummer'].strip()
        
    message = template.render(user=user.props, match=match.props)
    post_fields = {'message': message, "phone": phone}     # Set POST fields here

    request = Request(URL, urlencode(post_fields).encode())
    json = urlopen(request).read().decode()
    print(json)
    print(message)
    
    
def send_feedback_message(user):
    phone = user.props['Gsmnummer'].strip()
        
    message = feedback.render(user=user.props)
    post_fields = {'message': message, "phone": phone}     # Set POST fields here

    request = Request(URL, urlencode(post_fields).encode())
    json = urlopen(request).read().decode()
    print(json)
    print(message) 
    
def send_confirm_message(user):
    phone = user.props['Gsmnummer'].strip()
        
    message = confirm.render(user=user.props)
    post_fields = {'message': message, "phone": phone}     # Set POST fields here

    request = Request(URL, urlencode(post_fields).encode())
    json = urlopen(request).read().decode()
    print(json)
    print(message)

def send_feedback():
    persons = []
    with open(FILE, 'r', encoding="utf-8") as csvFile:
        buddyReader = csv.DictReader(csvFile, delimiter=',', quotechar='"')
        for row in buddyReader:
            if(row["Schooltype"] == "Middelbaar"):
                continue
            newbuddy = Buddy(row)

            # Make sure no double phone numbers enter
            for buddy in persons:
                if buddy.props["Gsmnummer"] == newbuddy.props["Gsmnummer"]:
                    print("Dubbele entry gevonden:", buddy)
                    persons.remove(buddy)
                    break

            persons.append(newbuddy)

    for buddy in persons:
        send_feedback_message(buddy)
        sleep(60)

def send_confirm():
    persons = []
    with open(FILE, 'r', encoding="utf-8") as csvFile:
        buddyReader = csv.DictReader(csvFile, delimiter=',', quotechar='"')
        for row in buddyReader:
            if(row["Schooltype"] == "Middelbaar"):
                continue
            newbuddy = Buddy(row)

            # Make sure no double phone numbers enter
            for buddy in persons:
                if buddy.props["Gsmnummer"] == newbuddy.props["Gsmnummer"]:
                    print("Dubbele entry gevonden:", buddy)
                    persons.remove(buddy)
                    break

            persons.append(newbuddy)
    
    print(len(persons))
    for buddy in persons:
        send_confirm_message(buddy)
        sleep(30)

def send_match():
    with open(FILE, 'r', encoding="utf-8") as csvFile:
        buddyReader = csv.DictReader(csvFile, delimiter=',', quotechar='"')
        for row in buddyReader:
            if(row["Schooltype"] == "Middelbaar"):
              continue
            newbuddy = Buddy(row)

            # Make sure no double phone numbers enter
            for buddy in BUDDIES:
                if buddy.props["Gsmnummer"] == newbuddy.props["Gsmnummer"]:
                    print("Dubbele entry gevonden:", buddy)
                    BUDDIES.remove(buddy)
                    break

            BUDDIES.append(newbuddy)

    printStatistics()

    matches = matchmaker()
    for match in matches:
        send_match_message(match[0], match[1])
        sleep(60)
        send_match_message(match[1], match[0])
        sleep(60)
        print(match[0].props["Naam"][:20].ljust(22), match[0].props["District"][:14].ljust(16), match[0].props["Schooltype"][:18].ljust(20), end="")
        print(" - ", end="")
        print(match[1].props["Naam"][:20].ljust(22), match[1].props["District"][:14].ljust(16), match[1].props["Schooltype"][:18].ljust(20))
if __name__ == "__main__":
    #send_feedback()
    #send_confirm()
    send_match()