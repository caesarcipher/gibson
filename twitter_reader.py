#NOTE: you must create oauth_tokens your self... It must include the constants
#shown below
from oauth_tokens import *
import twitter
import time 
import re
import send_event
import traceback
import sets 
REAL_TIME_PAUSE = True
REAL_TIME_SCALEFACTOR = 10 # time moves faster if this < 1
import tempfile
import urllib2
import sys
import os 
from threading import Thread
from Queue import Queue

def findMentions(tweet):
    iter =  re.finditer(r'(\A|\s)@(\w+)', tweet)
    return iter


class StatusGetter(Thread):
    
    def __init__(self, queue,wait=30):
        Thread.__init__(self)
        self.queue = queue
        self.api = twitter.Api(CONSUMER_KEY, CONSUMER_SECRET, USER_ACCESS_TOKEN,
        ACCESS_TOKEN_SECRET)
        self.since_id = None
        self.wait =wait

    def format(self, u):
        if self.since_id==None or u.GetId() > self.since_id:
            self.since_id = u.GetId()
        timesent = u.GetCreatedAtInSeconds()
        if u.text.find("@") > 0:
            type = "Mention"
            mentions = list()
            for m in findMentions(u.text):
                mentions.append(m.group(0))
                
            mentions = ",".join(mentions)
        else:
            type = "Status"
            mentions = ""
            
        
        return "|".join([str(timesent), type, "ALARM", u.user.screen_name, "N/A", mentions, "N/A", u.text])
 
     
    def run(self):
        while 1:
            try:
                totalWait = 0
                statuses = self.api.GetFriendsTimeline(since_id=self.since_id)
                startTime = statuses[-1].GetCreatedAtInSeconds()
               
                for status in range(len(statuses)-1, 0, -1):
                    status = statuses[status]
                    message = self.format(status)
                    self.queue.put(message)
                    
                    if REAL_TIME_PAUSE:
                        print "Wating %i seconds"%((status.GetCreatedAtInSeconds() - startTime)/REAL_TIME_SCALEFACTOR)
                        time.sleep( (status.GetCreatedAtInSeconds() - startTime)/REAL_TIME_SCALEFACTOR)
                        totalWait += ((status.GetCreatedAtInSeconds() - startTime)/REAL_TIME_SCALEFACTOR)
                    startTime = status.GetCreatedAtInSeconds()
            except:
                traceback.print_exc()
                pass # most likely a connection error...so lets try again later...
            print "sleeping..."
            if totalWait < self.wait:
                time.sleep(self.wait- totalWait)
            

class FriendFollowerGetter(Thread):
    def __init__(self, queue, wait=10):
        Thread.__init__(self)
        self.queue = queue
        self.api = twitter.Api(CONSUMER_KEY, CONSUMER_SECRET, USER_ACCESS_TOKEN,
        ACCESS_TOKEN_SECRET)
        self.friendList = []
        self.followerList = []
        self.followerIdList = set()
        self.wait =wait
        

    def formatList(self, lstType, lst):
        lstString = ",".join(lst)
        return "|".join( [str( int(time.time() * 1000)), lstType, lstString])
    
    def formatFOAFList(self, username, lst):
        lst = [ "@%s"%l for l in lst]
        lstString = ",".join(lst)
        return "|".join([ str(int(time.time() * 1000)), "foaf", "@%s"%username, lstString])
    
        
    def run(self):
        
        self.friendList = self.api.GetFriends()
        friendList = [ "@%s"%u.screen_name for u in self.friendList]
        message = self.formatList("friendList", friendList)
        self.queue.put(message)
        [ self.followerIdList.add(u.screen_name) for u in self.friendList]
        #print message
        self.followerList = self.api.GetFollowers()
        followerList = [ "@%s"%u.screen_name for u in self.followerList]
        message = self.formatList("followerList", followerList)
        [self.followerIdList.add(u.screen_name) for u in self.followerList]
        #socket.send_event(self._ip, self._port, message.encode("ascii", "replace"))
        #print message
        self.queue.put(message)
        imagegetter = ImageDownloader(self.queue, self.followerList, self.friendList)
        imagegetter.start()
        lastFollowerCall = 0
        #if (time.time() - lastFollowerCall ) > self.wait:
        while 1:
            try:
                if len(self.followerIdList)>0:             
                  userId = self.followerIdList.pop()
                            
                  f = self.api.GetFriends(userId)
                  message = self.formatFOAFList(userId, [u.screen_name for u in f])
                  self.queue.put(message)
                        #socket.send_event(self._ip, self._port, message.encode("ascii", "replace"))
                        #print message
                        
                else:
                    break
                    
            except:
                    traceback.print_exc()
            time.sleep(self.wait)

class ImageDownloader(Thread):
    def __init__(self, queue, followerList, friendList):
        Thread.__init__(self)
        self.queue = queue
        self.followerList = followerList
        self.friendList = friendList
        
    def run(self):
        for fr in self.friendList:
            url = fr.profile_image_url
            username = fr.screen_name
            try:
                u = urllib2.urlopen(url)
                basename, ext = os.path.splitext(url)
                localfilename = tempfile.mkstemp(".%s"%ext)
                f = file(localfilename[1], "w+b")
                f.write(u.read())
                f.close()
                message = self.format(username, localfilename[1])
                self.queue.put(message)
            except:
                traceback.print_exc()
            if fr.status:
                message = self.formatInitStatus(username, fr.status.text)
            self.queue.put(message)
        for fr in self.followerList:
            url = fr.profile_image_url
            username = fr.screen_name
            try:
                u = urllib2.urlopen(url)
                basename, ext = os.path.splitext(url)
                localfilename = tempfile.mkstemp("%s"%ext)
                f = file(localfilename[1], "w+b")
                f.write(u.read())
                f.close()
                message = self.format(username, localfilename[1])
                self.queue.put(message)
            except:
                traceback.print_exc()
            if fr.status:
                message = self.formatInitStatus(username, fr.status.text)
    def formatInitStatus(self, username, status):
        return "|".join([ str(int(time.time() * 1000)), "InitStatus", username, status])
        
    def format(self, username, filename):
        return "|".join([str( int(time.time()) *1000), "textureFile", username, filename])
            
class TwitterReader():

    def __init__(self, ip, port):
        self._port  = port
        self._ip = ip
        self.followerIdList = sets.Set()



    def formatList(self, lstType, lst):
        lstString = ",".join(lst)
        return "|".join( [str( int(time.time() * 1000)), lstType, lstString])
        
    def formatFOAFList(self, username, lst):
        lst = [ "@%s"%l for l in lst]
        lstString = ",".join(lst)
        return "|".join([ str(int(time.time() * 1000)), "foaf", "@%s"%username, lstString])
    
    def run(self):
        self.queue = Queue()
        self.statuses = StatusGetter(self.queue)
        self.friends = FriendFollowerGetter(self.queue)
        self.statuses.start()
        self.friends.start()
        self.socket = send_event.EncapsulateForPanda()
        while 1:
            try:
                message = self.queue.get()
                print message
                self.socket.send_event(self._ip, self._port, message.encode("ascii","replace"))
            except KeyboardInterrupt, e:
                break
            except:
                traceback.print_exc()
                
    
    #def run(self):
    #    a = twitter.Api(CONSUMER_KEY, CONSUMER_SECRET, USER_ACCESS_TOKEN,
    #    ACCESS_TOKEN_SECRET)
    #    self.since_id = None
    #    socket = send_event.EncapsulateForPanda()
    #    friends = a.GetFriends()
    #    friendList = [ "@%s"%u.screen_name for u in friends]
    #    message = self.formatList("friendList", friendList)
    #    socket.send_event(self._ip, self._port, message.encode("ascii","replace"))
    #    [ self.followerIdList.add(u.screen_name) for u in friends]
    #    print message
    #    followers = a.GetFollowers()
    #    followerList = [ "@%s"%u.screen_name for u in followers]
    #    message = self.formatList("followerList", followerList)
    #    [self.followerIdList.add(u.screen_name) for u in followers]
    #    socket.send_event(self._ip, self._port, message.encode("ascii", "replace"))
    #    print message
    #    lastFollowerCall = 0
    #    while 1:
    #        try:
    #            totalWait = 0
    #            if (time.time() - lastFollowerCall ) > 15:
    #                try:
    #                    userId = self.followerIdList.pop()
    #                    f = a.GetFriends(userId)
    #                    message = self.formatFOAFList(userId, [u.screen_name for u in f])
    #                    socket.send_event(self._ip, self._port, message.encode("ascii", "replace"))
    #                    print message
    #                    lastFollowerCall = time.time()
    #                except:
    #                    pass
    #            statuses = a.GetFriendsTimeline(since_id=self.since_id)
    #            startTime = statuses[-1].GetCreatedAtInSeconds()
    #           
    #            for status in range(len(statuses)-1, 0, -1):
    #                status = statuses[status]
    #                message = self.format(status)
    #                socket.send_event(self._ip, self._port, message.encode("ascii", 'replace'))
    #                print message
    #                #print status.GetCreatedAtInSeconds() - startTime
    #                if REAL_TIME_PAUSE:
    #                    print "Wating %i seconds"%((status.GetCreatedAtInSeconds() - startTime)/REAL_TIME_SCALEFACTOR)
    #                    time.sleep( (status.GetCreatedAtInSeconds() - startTime)/REAL_TIME_SCALEFACTOR)
    #                    totalWait += ((status.GetCreatedAtInSeconds() - startTime)/REAL_TIME_SCALEFACTOR)
    #                startTime = status.GetCreatedAtInSeconds()
    #        except KeyboardInterrupt, e:
    #            break
    #        except:
    #            traceback.print_exc()
    #            pass # most likely a connection error...so lets try again later...
    #        print "sleeping..."
    #        if totalWait < 15:
    #            time.sleep(15 - totalWait)

if __name__=="__main__":
    reader = TwitterReader()
    reader.run()


        
