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
from jinja2 import Environment, FileSystemLoader

rootDir = "/root/"
configDir = rootDir+"phone-conf/"
debugEnable = True
debugConf = True

# log a message
def log(*args):
    with open(logFileName, "a") as logFile:
        message = time.asctime(time.localtime())+","
        for arg in args:
            message += arg.__str__()+","
        logFile.write(message.rstrip(",")+"\n")

# log a debug message
def debug(*args):
    if debugEnable:   # global debug flag enables debugging
        try:
            if globals()[args[0]]:
                message = args[1]+" "   # first argument is the object doing the logging
                for arg in args[2:]:
                    message += arg.__str__()+" "
                if sysLogging:
                    syslog.syslog(message)
                else:
                    print message
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
                    debug("debugEnable", "error evaluating", configLine)
    except:
        debug("debugEnable", "error reading", configDir+configFileName)
        
# read data
#whitelist = json.load(open(dataDir+"whitelist"))
#blacklist = json.load(open(dataDir+"blacklist"))
#smsForward = json.load(open(dataDir+"smsForward"))
phoneData = json.load(open(dataDir+"phone.json"))
debug("debugEnable", "phone", str(phoneData))

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
    if number != "":
        return "%s %s-%s" % (number[2:5], number[5:8], number[8:])
    else:
        return ""
    
class WebRoot(object):
    def __init__(self, env):
        self.env = env
            
    # Web UI    
    @cherrypy.expose
    def index(self, action=None, resource=None):
        reply = ""
        title="Phone screening"
        for To in phoneData.keys():
            # format the whitelist
            whiteDisp = []
            for w in phoneData[To]["whitelist"].keys():
                whiteDisp += [[phoneFmt(w), phoneData[To]["whitelist"][w][0], phoneData[To]["whitelist"][w][1], [phoneFmt(f) for f in phoneData[To]["whitelist"][w][2]]]]
            # format the blacklist
            blackDisp = []
            for b in phoneData[To]["blacklist"].keys():
                blackDisp += [[phoneFmt(b), phoneData[To]["blacklist"][b]]]
            # format the log file
            with open(logFileName) as logFile:
                logLines = [logLine.rstrip('\n').split(",") for logLine in logFile]
            logLines.sort(reverse=True)
            logDisp = []
            for logLine in logLines:
                while len(logLine) < 6:
                    logLine += [""]
                if logLine[3] == To:
                    logDisp += [[logLine[0], logLine[1], phoneFmt(logLine[2]), logLine[4], [phoneFmt(f) for f in logLine[5].split("|")]]]
            # build the web page
            reply += self.env.get_template("default.html").render(title=title, script="",
                                number=phoneFmt(To), 
                                white=whiteDisp,
                                black=blackDisp,
                                log=logDisp)
            title = ""
        return reply

    # Answer an incoming call    
    @cherrypy.expose
    def answer(self, From, FromZip, FromCity, ApiVersion, To, ToCity, CalledState, FromState, 
               Direction, CallStatus, ToZip, CallerCity, FromCountry, CalledCity, 
               CalledCountry, Caller, CallerState, AccountSid, Called, CallerCountry, 
               CalledZip, CallerZip, CallSid, ToCountry, ToState):
        debug("debugEnable", "phone", "call from", From, "to", To)
        logMsg = "incoming,"+From+","+To
        cherrypy.response.headers['Content-Type'] = "text/xml"
        response  = "<?xml version='1.0' encoding='UTF-8'?>\n"
        response += "<Response>\n"
        if From in phoneData[To]["whitelist"].keys():
            debug("debugEnable", "phone", From, "is in whitelist")
            logMsg += ",forwarded,"
            response += "   <Dial timeout='"+str(timeout)+"' action='record' method='GET'>"
            debug("debugEnable", "phone", "forwarding to", str(phoneData[To]["whitelist"][From][2]))
            for number in phoneData[To]["whitelist"][From][2]:
                response += "<Number>"+number+"</Number>\n"
                logMsg += number+"|"
            logMsg = logMsg.rstrip("|")
            response += "</Dial>\n"
        elif From in phoneData[To]["blacklist"].keys():
            debug("debugEnable", "phone", From, "is in blacklist")
            logMsg += ",rejected"
            response += "   <Reject reason='busy' />\n"
        else:
            debug("debugEnable", "phone", From, "is unknown")
            logMsg += ",unknown"
            response += "   <Say voice='"+phoneData[To]["recordingVoice"]+"' language='"+phoneData[To]["recordingLanguage"]+"'>"+phoneData[To]["unknownMessage"]+"</Say>\n"
            response += "   <Record action='save' maxLength='"+maxlength+"' method='GET'/>\n"        
        response += "</Response>\n"
        log(logMsg)
        return response

    # Record a voicemail from a whitelisted number    
    @cherrypy.expose
    def record(self, From, FromZip, FromCity, ApiVersion, To, ToCity, CalledState, FromState, 
               Direction, CallStatus, ToZip, CallerCity, FromCountry, CalledCity, 
               CalledCountry, Caller, CallerState, AccountSid, Called, CallerCountry, 
               CalledZip, CallerZip, CallSid, ToCountry, ToState,
               DialCallSid, DialCallStatus):
        debug("debugEnable", "phone", "recording voicemail from", From)
        logMsg = "recording,"+From+","+To
        cherrypy.response.headers['Content-Type'] = "text/xml"
        response  = "<?xml version='1.0' encoding='UTF-8'?>\n"
        response += "<Response>\n"
        response += "   <Say voice='"+phoneData[To]["recordingVoice"]+"' language='"+phoneData[To]["recordingLanguage"]+"'>"+phoneData[To]["whitelistMessage"]+"</Say>\n"
        response += "   <Record action='save' maxLength='"+str(maxlength)+"' method='GET'/>\n"        
        response += "</Response>\n"
        log(logMsg)
        return response

    # Save a recorded voicemail   
    @cherrypy.expose
    def save(self, From, FromZip, FromCity, ApiVersion, To, ToCity, CalledState, FromState, 
               Direction, CallStatus, ToZip, CallerCity, FromCountry, CalledCity, 
               CalledCountry, Caller, CallerState, AccountSid, Called, CallerCountry, 
               CalledZip, CallerZip, CallSid, ToCountry, ToState,
               RecordingUrl, RecordingDuration, RecordingSid, Digits=None):
        debug("debugEnable", "phone", "received", RecordingDuration, "second voicemail from", From)
        logMsg = "recorded,"+From+","+To+","+str(RecordingDuration)
        
        # copy the file from Twilio's server
        twilioUrl = urllib.unquote(RecordingUrl)+".mp3"
        fileName = time.strftime("%Y%m%d%H%M%S")
        mp3File = fileName+".mp3"
        command = "wget "+twilioUrl+" -O "+filePath+mp3File
        debug("debugEnable", "phone", "copying recording from", twilioUrl, "to", filePath+mp3File)
        os.system(command)
        
        # send the notification if it is longer than the minimum time
        if int(RecordingDuration) > minRecording:
            debug("debugEnable", "phone", "sending notification")
            # send the email announcing the voicemail
            subject = "New voicemail from "+phoneFmt(Caller)
            message  = "You have a new voicemail from "+phoneFmt(Caller)+"\n"
            message += "http://"+urlPath+mp3File
            if notifyEmail: sendEmail(mailFrom, mailTo, subject, message)
            if notifySms: sendSms(To, phoneData[To]["notifyNumbers"], message)
        else:
            debug("debugEnable", "phone", "recording too short to send notification")
            
        log(logMsg)
        response = ""
        return response
        
    # Retrieve a voicemail
    @cherrypy.expose
    def voicemail(self, vm):
        try:
            vmFile = open(filePath+vm)
            vMsg = vmFile.read()
            vmFile.close()
        except:
            debug("debugEnable", "phone", vm, "not found")
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
        debug("debugEnable", "phone", "SMS from", From, "to", To)
        logMsg = "text,"+From+","+To+","
        try:
            Forward = smsForward[To]
            logMsg += Forward
            debug("debugEnable", "phone", "forwarding to", Forward)
            cherrypy.response.headers['Content-Type'] = "text/xml"
            response  = "<?xml version='1.0' encoding='UTF-8'?>\n"
            response += "<Response>\n"
            response += "   <Message to='"+Forward+"'>\n"
            response += "       From "+From+": "+Body+"\n"
            response += "   </Message>\n"
            response += "</Response>\n"
            return response
        except:
            debug("debugEnable", "phone", To, "not in SMS forwrding list")
            logMsg += "unknown"
        log(logMsg)
        
if __name__ == "__main__":
    # set up the web server
    baseDir = os.path.abspath(os.path.dirname(__file__))
    globalConfig = {
        'server.socket_port': webPort,
        'server.socket_host': "0.0.0.0",
        }
    appConfig = {
        '/css': {
            'tools.staticdir.on': True,
            'tools.staticdir.root': os.path.join(baseDir, "static"),
            'tools.staticdir.dir': "css",
        },
        '/js': {
            'tools.staticdir.on': True,
            'tools.staticdir.root': os.path.join(baseDir, "static"),
            'tools.staticdir.dir': "js",
        },
        '/favicon.ico': {
            'tools.staticfile.on': True,
            'tools.staticfile.filename': os.path.join(baseDir, "static/favicon.ico"),
        },
    }    
    cherrypy.config.update(globalConfig)
    root = WebRoot(Environment(loader=FileSystemLoader(os.path.join(baseDir, 'templates'))))
    cherrypy.tree.mount(root, "/", appConfig)
    if not webLogging:
        access_log = cherrypy.log.access_log
        for handler in tuple(access_log.handlers):
            access_log.removeHandler(handler)
    cherrypy.engine.timeout_monitor.unsubscribe()
    cherrypy.engine.autoreload.unsubscribe()
    cherrypy.engine.start()

