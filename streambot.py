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
    
    if since_last > timedelta(hours=1):
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
        
    countresponse += "<http://realcount.club/|more>"
    countresponse = countresponse.replace("realDonaldTrump", "RDT")
    print countresponse

def post_message(channel, response, username=None, pic=None):
    if username is None:
        slack_client.api_call("chat.postMessage", channel=channel, text=response, as_user=True)
    else:
        slack_client.api_call("chat.postMessage", channel=channel, text=response, as_user=False, username=username, icon_url=pic, unfurl_media=True)
    # print(response)

handles = {818910970567344128: 'VP1', 25073877: 'realDonaldTrump', 822215679726100480: 'POTUS', 836598396165230594: 'predickit'}

# This is the listener, resposible for receiving data
class StdOutListener(tweepy.StreamListener):
            
    def on_delete(self, status_id, user_id):
        url = "https://twitter.com/" + handles[user_id] + "/" + str(status_id)
        response = handles[user_id] + " DELETION!!!"
        channel = "#twitteralert"
        
        if user_id == 836598396165230594:
            print url
            channel = "#test"
            
        post_message(channel,response)
        print response
        get_counts()
        post_message(channel,countresponse)
        
        channel = "#general"
        if user_id == 836598396165230594:
            channel = "#test"
            
        post_message(channel,response+"\n"+countresponse+"\nDeleted tweet: "+url)
        
        return
    
    def on_status(self, status):
        #print status
        
        channel1 = "#general"
        channel2 = "#twitteralert"
        testchannel = "#test"
        
        url = "https://twitter.com/"+status.user.screen_name+"/status/"+str(status.id)
        
        if status.truncated:
            vpresponse, sep, tail = status.extended_tweet['full_text'].partition('http')
            #source = status.extended_tweet['source']
        else:
            vpresponse, sep, tail = status.text.partition('http')
            #source = status.source
        
        #sourceresponse = "\nSource: "+source
        
        #response = "*@"+status.user.screen_name+" tweet!* "+url
        #vpresponse = "*@"+status.user.screen_name+" tweet!* "+head
        #get the current counts
        get_counts()
        
        at_name = "@" + status.user.screen_name+ " tweet!"
        response = url + "\n" + countresponse# + sourceresponse
        vpresponse = vpresponse + "\n" + countresponse# + sourceresponse
        
        if status.user.screen_name != 'predickit':
            post_message(channel2, response, at_name, status.user.profile_image_url)
            if status.user.screen_name == 'VP':
                post_message(channel1, vpresponse, at_name, status.user.profile_image_url)
            else:
                post_message(channel1, response, at_name, status.user.profile_image_url)
        if status.user.screen_name == 'predickit':
            post_message(testchannel, response, at_name, status.user.profile_image_url)
        
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
