# -*- coding: iso-8859-15 -*-

import os
import urllib
import cherrypy
import syslog
import time
import json
import smtplib
from email.mime.text import MIMEText
from twilio.rest import TwilioRestClient

rootDir = "/root/"
configDir = rootDir+"phone-conf/"
debugEnable = True
debugConf = True

# log a message
def log(*args):
    message = args[0]+" "   # first argument is the object doing the logging
    for arg in args[1:]:
        message += arg.__str__()+" "
    if sysLogging:
        syslog.syslog(message)
    else:
        print message

# log a debug message
def debug(*args):
    if debugEnable:   # global debug flag enables debugging
        try:
            if globals()[args[0]]:
                log(*args[1:])
        except:
            pass
            
# read configuration files
for configFileName in os.listdir(configDir):
    debug('debugConf', "config open", configFileName)
    try:
        with open(configDir+configFileName) as configFile:
            configLines = [configLine.rstrip('\n') for configLine in configFile]
        for configLine in configLines:
            if (len(configLine) > 0) and (configLine[0] != "#"):
                try:
                    exec(configLine)
                    debug('debugConf', "config read", configLine)
                except:
                    log("config", "error evaluating", configLine)
    except:
        log("config", "error reading", configDir+configFileName)
        
# read data
whitelist = json.load(open(dataDir+"whitelist"))
blacklist = json.load(open(dataDir+"blacklist"))
smsForward = json.load(open(dataDir+"smsForward"))

# get the value of a variable from a file
def getValue(fileName):
    return json.load(open(fileName))

# send an email notification    
def sendEmail(fromAddr, toAddr, subject, message):
    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = fromAddr
    msg['To'] = toAddr
    s = smtplib.SMTP('localhost')
    s.sendmail(fromAddr, [toAddr], msg.as_string())
    s.quit()

# send an sms notification
def sendSms(notifyFromNumber, notifyNumbers, message):
    smsClient = TwilioRestClient(getValue(smsSid), getValue(smsToken))
    smsFrom = notifyFromNumber
    for smsTo in notifyNumbers:
        smsClient.sms.messages.create(to=smsTo, from_=smsFrom, body=message)

# format a phone number for display
def phoneFmt(number):
    return "%s %s-%s" % (number[2:5], number[5:8], number[8:])
    
class WebRoot(object):
    def __init__(self):
        pass
            
    # Answer an incoming call    
    @cherrypy.expose
    def answer(self, From, FromZip, FromCity, ApiVersion, To, ToCity, CalledState, FromState, 
               Direction, CallStatus, ToZip, CallerCity, FromCountry, CalledCity, 
               CalledCountry, Caller, CallerState, AccountSid, Called, CallerCountry, 
               CalledZip, CallerZip, CallSid, ToCountry, ToState):
        if debugEnable: log("phone", "call from", From, "to", To)
        cherrypy.response.headers['Content-Type'] = "text/xml"
        response  = "<?xml version='1.0' encoding='UTF-8'?>\n"
        response += "<Response>\n"
        if From in whitelist.keys():
            if debugEnable: log("phone", From, "is in whitelist")
            response += "   <Dial timeout='"+timeout+"' action='record' method='GET'>"
            if debugEnable: log("phone", "forwarding to", str(whitelist[From][2]))
            for number in whitelist[From][2]:
                response += "<Number>"+number+"</Number>\n"
            response += "</Dial>\n"
        elif From in blacklist.keys():
            if debugEnable: log("phone", From, "is in blacklist")
            response += "   <Reject reason='busy' />\n"
        else:
            if debugEnable: log("phone", From, "is unknown")
            response += "   <Say voice='alice' language='"+recordingLanguage+"'>"+unknownMessage+"</Say>\n"
            response += "   <Record action='save' maxLength='"+maxlength+"' method='GET'/>\n"        
        response += "</Response>\n"
        return response

    # Record a voicemail from a whitelisted number    
    @cherrypy.expose
    def record(self, From, FromZip, FromCity, ApiVersion, To, ToCity, CalledState, FromState, 
               Direction, CallStatus, ToZip, CallerCity, FromCountry, CalledCity, 
               CalledCountry, Caller, CallerState, AccountSid, Called, CallerCountry, 
               CalledZip, CallerZip, CallSid, ToCountry, ToState,
               DialCallSid, DialCallStatus):
        if debugEnable: log("phone", "recording voicemail from", From)
        cherrypy.response.headers['Content-Type'] = "text/xml"
        response  = "<?xml version='1.0' encoding='UTF-8'?>\n"
        response += "<Response>\n"
        response += "   <Say>"+whitelistMessage+"</Say>\n"
        response += "   <Record action='save' maxLength='"+maxlength+"' method='GET'/>\n"        
        response += "</Response>\n"
        return response

    # Save a recorded voicemail   
    @cherrypy.expose
    def save(self, From, FromZip, FromCity, ApiVersion, To, ToCity, CalledState, FromState, 
               Direction, CallStatus, ToZip, CallerCity, FromCountry, CalledCity, 
               CalledCountry, Caller, CallerState, AccountSid, Called, CallerCountry, 
               CalledZip, CallerZip, CallSid, ToCountry, ToState,
               RecordingUrl, RecordingDuration, RecordingSid, Digits=None):
        if debugEnable: log("phone", "received", RecordingDuration, "second voicemail from", From)
        
        # copy the file from Twilio's server
        twilioUrl = urllib.unquote(RecordingUrl)+".mp3"
        fileName = time.strftime("%Y%m%d%H%M%S")
        mp3File = fileName+".mp3"
        command = "wget "+twilioUrl+" -O "+filePath+mp3File
        if debugEnable: log("phone", "copying recording from", twilioUrl, "to", filePath+mp3File)
        os.system(command)
        
        # send the notification if it is longer than the minimum time
        if int(RecordingDuration) > minRecording:
            if debugEnable: log("phone", "sending notification")
            # send the email announcing the voicemail
            subject = "New voicemail from "+phoneFmt(Caller)
            message  = "You have a new voicemail from "+phoneFmt(Caller)+"\n"
            message += "http://"+urlPath+mp3File
            if notifyEmail: sendEmail(mailFrom, mailTo, subject, message)
            if notifySms: sendSms(notifyFromNumber, notifyNumbers, message)
        else:
            if debugEnable: log("phone", "recording too short to send notification")

    # Retrieve a voicemail
    @cherrypy.expose
    def voicemail(self, vm):
        try:
            vmFile = open(filePath+vm)
            vMsg = vmFile.read()
            vmFile.close()
        except:
            if debugEnable: log("phone", vm, "not found")
            cherrypy.response.status = 404
            return ""
        cherrypy.response.headers['Content-Type'] = "audio/x-mp3"
        cherrypy.response.headers['Content-Range'] = "bytes 0-"
        return vMsg
                
    # SMS message forwarding  
    @cherrypy.expose
    def sms(self, From, FromZip, FromCity, ApiVersion, To, ToCity, FromState, 
               ToZip, FromCountry, ToCountry, ToState, AccountSid, 
               Body, MessageSid, SmsStatus, SmsMessageSid, NumMedia, SmsSid):
        if debugEnable: log("phone", "SMS from", From, "to", To)
        try:
            Forward = smsForward[To]
            if debugEnable: log("phone", "forwarding to", Forward)
            cherrypy.response.headers['Content-Type'] = "text/xml"
            response  = "<?xml version='1.0' encoding='UTF-8'?>\n"
            response += "<Response>\n"
            response += "   <Message to='"+Forward+"'>\n"
            response += "       From "+From+": "+Body+"\n"
            response += "   </Message>\n"
            response += "</Response>\n"
            return response
        except:
            if debugEnable: log("phone", To, "not in SMS forwrding list")
        
if __name__ == "__main__":
    # set up the web server
    baseDir = os.path.abspath(os.path.dirname(__file__))
    globalConfig = {
        'server.socket_port': webPort,
        'server.socket_host': "0.0.0.0",
        }
    appConfig = {}    
    cherrypy.config.update(globalConfig)
    root = WebRoot()
    cherrypy.tree.mount(root, "/", appConfig)
    if not webLogging:
        access_log = cherrypy.log.access_log
        for handler in tuple(access_log.handlers):
            access_log.removeHandler(handler)
    cherrypy.engine.timeout_monitor.unsubscribe()
    cherrypy.engine.autoreload.unsubscribe()
    cherrypy.engine.start()

