import tweepy, json
import time
import urllib
from slackclient import SlackClient
from datetime import datetime

url = 'http://realcount.club/data.json'
lithiumdata = urllib.urlopen(url)
data = json.loads(lithiumdata.read())

def load_data():
    global data
    url = 'http://realcount.club/data.json'
    lithiumdata = urllib.urlopen(url)
    data = json.loads(lithiumdata.read())

    # load previous counts
    global prevcounts
    prevcounts = json.load(open('prevcounts.json', 'r'))
    
    print "Loading previous counts"
    
def get_counts():
    global countresponse
    print "Updating counts...."
    # call twitter api for each
    potus = api.get_user('potus')
    rdt = api.get_user('realDonaldTrump')
    vp = api.get_user('vp')
    
    data['potuscount'] = potus.statuses_count - data['potusnum']
    data['rdtcount'] = rdt.statuses_count - data['rdtnum']
    data['vpcount'] = vp.statuses_count - data['vpnum']
    
    countresponse = "<" + data['potuslink'] + "|*POTUS*> " + str(data['potuscount']) + "       <" + data['rdtlink'] + "|*RDT*> " + str(data['rdtcount']) + "       <" + data['vplink'] + "|*VP*> " + str(data['vpcount']) + "       <http://realcount.club/|more>"
    
    prevcounts['vp'] = data['vpcount']
    prevcounts['rdt'] = data['rdtcount']
    prevcounts['potus'] = data['potuscount']
    with open('prevcounts.json', 'w') as fp: json.dump(prevcounts, fp)
    
    print "POTUS "+str(data['potuscount'])+"     RDT: "+str(data['rdtcount'])+"     VP:"+str(data['vpcount'])

def post_message(channel, response, username=None, pic=None):
    if username is None:
        slack_client.api_call("chat.postMessage", channel=channel, text=response, as_user=True)
    else:
        slack_client.api_call("chat.postMessage", channel=channel, text=response, as_user=False, username=username, icon_url=pic, unfurl_media=True)
    # print(response)
    
    
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



# This is the listener, resposible for receiving data
class StdOutListener(tweepy.StreamListener):    
    def on_delete(self, status_id, user_id):
        if user_id == 818910970567344128:
            response = "VP DELETION!!!"
            channel = "#alert"
        elif user_id == 25073877:
            response = "RDT DELETION!!!"
            channel = "#alert"
        elif user_id == 822215679726100480:
            response = "POTUS DELETION!!!"
            channel = "#alert"
        elif user_id == 836598396165230594:
            channel = "#test"
            response = "predickit DELETION!!!"
            
        post_message(channel,response)
        print response
        get_counts()
        post_message(channel,countresponse)
        
        if user_id == 818910970567344128:
            channel = "#general"
        elif user_id == 25073877:
            channel = "#general"
        elif user_id == 822215679726100480:
            channel = "#general"
        elif user_id == 836598396165230594:
            return
        
        post_message(channel,response+"\n"+countresponse)
        
        return
    
    def on_status(self, status):
        channel1 = "#general"
        channel2 = "#twitteralert"
        testchannel = "#test"
        
        url = "https://twitter.com/"+status.user.screen_name+"/status/"+str(status.id)
        
        if status.truncated:
            vpresponse, sep, tail = status.extended_tweet['full_text'].partition('http')
        else:
            vpresponse, sep, tail = status.text.partition('http')
        
        #response = "*@"+status.user.screen_name+" tweet!* "+url
        #vpresponse = "*@"+status.user.screen_name+" tweet!* "+head
        #reload the data
        load_data()
        
        #get the current counts
        get_counts()
        
        at_name = "@" + status.user.screen_name+ " tweet!"
        response = url + "\n" + countresponse
        vpresponse = vpresponse + "\n" + countresponse
        
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
        print status

if __name__ == '__main__':
    load_data()
    get_counts()
    response = "<" + data['potuslink'] + "|*POTUS*> " + str(data['potuscount']) + "       <" + data['rdtlink'] + "|*RDT*> " + str(data['rdtcount']) + "       <" + data['vplink'] + "|*VP*> " + str(data['vpcount']) + "       <http://realcount.club/|more>"
    post_message("#test", "Loading up streambot")
    post_message("#test", response)
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
