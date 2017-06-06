import tweepy, json
import time
import urllib
from slackclient import SlackClient
from datetime import datetime
from datetime import timedelta
from collections import OrderedDict

#load secrets
f = json.load(open('secrets.json', 'r'))
slack_token = f['slack_token']
BOT_ID = f['bot_id']

#twitter secrets
consumer_key = f['consumer_key']
consumer_secret = f['consumer_secret']
access_token=f['access_token']
access_token_secret=f['access_token_secret']

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)

#SLACK STUFF
AT_BOT = "<@" + BOT_ID + ">"
slack_client = SlackClient(slack_token)
BOT_NAME = 'autocountbot'

countresponse = ""


def get_since_last():
    global last_update_time
    global since_last
    try:
        since_last = datetime.now() - last_update_time
    except NameError:
        print "since_last not defined yet"
    else:
        print str(since_last.total_seconds())  + " seconds since last update"

def load_data():
    global lithium_data
    global last_update_time
    global since_last
    print "Loading the data from realcount.club ...."
    url = 'http://realcount.club/alldata.json'
    lithium_urllib = urllib.urlopen(url)
    lithium_data = json.loads(lithium_urllib.read())
    lithium_data = OrderedDict(sorted(lithium_data.items(), key=lambda t: t[0].lower()))
    last_update_time = datetime.now()
    get_since_last()

def reload_data():
    print "Checking for last update ...."
    get_since_last()
    
    if since_last > timedelta(minutes=10):
        load_data()
    else:
        print "Too soon to update from realcount.club again."

def get_counts():
    global countresponse
    countresponse = ""
    global lithium_data
    global tweet
    tweet = {}
    print "Updating counts ...."
    reload_data()
    
    # call twitter api for each
    
    for key in lithium_data:        
        tweet[lithium_data[key]['handle']]=api.get_user(lithium_data[key]['handle'])
        lithium_data[key]['count'] = tweet[lithium_data[key]['handle']].statuses_count - lithium_data[key]['num']
        countresponse += "<" + lithium_data[key]['link'] + "|*" + key + "*> " + str(lithium_data[key]['count']) + "        "
        
    countresponse = countresponse.replace("realDonaldTrump", "RDT")
    countresponse += "<http://realcount.club/|more>"
    print countresponse

def post_message(channel, response, username=None, pic=None):
    if username is None:
        slack_client.api_call("chat.postMessage", channel=channel, text=response, as_user=True)
    else:
        slack_client.api_call("chat.postMessage", channel=channel, text=response, as_user=False, username=username, icon_url=pic)
    # print(response)

handles = {818910970567344128: 'VP', 25073877: 'realDonaldTrump', 822215679726100480: 'POTUS', 836598396165230594: 'predickit'}

# This is the listener, resposible for receiving data
class StdOutListener(tweepy.StreamListener):
            
    def on_delete(self, status_id, user_id):
        global countresponse
        global lithium_data
        url = "https://twitter.com/" + handles[user_id] + "/" + str(status_id)
        response = handles[user_id] + " DELETION!!!"
        alertchannel = "#twitteralert"
        generalchannel = "#general"
        
        if user_id == 836598396165230594:
            print url
            alertchannel = "#test"
            generalchannel = "#test"
            
        post_message(generalchannel,response)
        print response
        
        quickcount = ""
        
        if handles[user_id] == "VP":
            lithium_data["VP-Fri"]['count'] -=1
            lithium_data["VP-Tue"]['count'] -=1
        elif handles[user_id] == "POTUS":
            lithium_data["POTUS"]['count'] -=1
        elif handles[user_id] == "realDonaldTrump":
            lithium_data["realDonaldTrump"]['count'] -=1
        
        for key in lithium_data:
            quickcount += "<" + lithium_data[key]['link'] + "|*" + key + "*> " + str(lithium_data[key]['count']) + "        "
        
        quickcount = quickcount.replace("realDonaldTrump", "RDT")
        quickcount += "<http://realcount.club/|more>"
        
        post_message(generalchannel,quickcount)
        
        time.sleep(5)
        get_counts()
        
        if quickcount != countresponse:
            post_message("#general","Count correction!\n"+countresponse)
            
        post_message(alertchannel,response+"\n"+countresponse+"\nDeleted tweet: "+url)
            
        post_message(generalchannel,"Deleted tweet: "+url)
        
        return
    
    def on_status(self, status):
        global countresponse
        global lithium_data
        #print status
        
        generalchannel = "#general"
        alertchannel = "#twitteralert"
        testchannel = "#test"
        
        at_name = "@" + status.user.screen_name+ " tweet!"
        
        url = "https://twitter.com/"+status.user.screen_name+"/status/"+str(status.id)
        response = url
        
        if status.user.screen_name != 'predickit':
            if status.user.screen_name == 'VP':
                if status.truncated:
                    response, sep, tail = status.extended_tweet['full_text'].partition('http')
                else:
                    response, sep, tail = status.text.partition('http')
            post_message(generalchannel, response, at_name, status.user.profile_image_url)
        else:
            post_message(testchannel, response, at_name, status.user.profile_image_url)
        
        quickcount = ""
        
        if status.user.screen_name == "VP":
            lithium_data["VP-Fri"]['count'] +=1
            lithium_data["VP-Tue"]['count'] +=1
        elif status.user.screen_name == "POTUS":
            lithium_data["POTUS"]['count'] +=1
        elif status.user.screen_name == "realDonaldTrump":
            lithium_data["realDonaldTrump"]['count'] +=1
            
        
        for key in lithium_data:
            quickcount += "<" + lithium_data[key]['link'] + "|*" + key + "*> " + str(lithium_data[key]['count']) + "        "
        
        quickcount = quickcount.replace("realDonaldTrump", "RDT")
        quickcount += "<http://realcount.club/|more>"
        print quickcount
        
        if status.user.screen_name != 'predickit':
            post_message(generalchannel, quickcount, at_name, status.user.profile_image_url)
            alertresponse = url + "\n" + quickcount
            post_message(alertchannel, alertresponse, at_name, status.user.profile_image_url)
            time.sleep(10)
            get_counts()
            if quickcount != countresponse:
                post_message(generalchannel, "Count correction!\n"+countresponse, at_name, status.user.profile_image_url)
        else:
            post_message(testchannel, quickcount, at_name, status.user.profile_image_url)
            time.sleep(5)
            get_counts()
            if quickcount != countresponse:
                post_message(testchannel, "Count correction!\n"+countresponse, at_name, status.user.profile_image_url)
            
        # if status.user.screen_name != 'predickit':
        #     post_message(alertchannel, countresponse, at_name, status.user.profile_image_url)
        #     if status.user.screen_name == 'VP':
        #         post_message(generalchannel, vpresponse, at_name, status.user.profile_image_url)
        #     else:
        #         post_message(generalchannel, response, at_name, status.user.profile_image_url)
        # if status.user.screen_name == 'predickit':
        #     post_message(testchannel, response, at_name, status.user.profile_image_url)
        #
        print at_name
        #print response  
        
    def on_error(self, status):
        print "Error"
        #print status
        
if __name__ == '__main__':
    load_data()
    get_counts()
    post_message("#test", "Loading up streambot...")
    post_message("#test", countresponse)
    print "Showing all tweets from my timeline"
    while True:
        l = StdOutListener()
        stream = tweepy.Stream(auth, l, timeout=60)

        try:
            stream.userstream()
            
        except Exception, e:
            print "Error. Restarting Stream.... Error: "
            print e.__doc__
            print e.message
