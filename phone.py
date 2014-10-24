# -*- coding: iso-8859-15 -*-

import os
import urllib
import cherrypy
import syslog
import time
import smtplib
from email.mime.text import MIMEText
from config import *

def log(*args):
    message = args[0]+" "
    for arg in args[1:]:
        message += arg.__str__()+" "
#    print message
    syslog.syslog(message)

def email(fromAddr, toAddr, subject, message):
    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = fromAddr
    msg['To'] = toAddr
    s = smtplib.SMTP('localhost')
    s.sendmail(fromAddr, [toAddr], msg.as_string())
    s.quit()

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
        if debug: log("phone", "call from", From, "to", To)
        cherrypy.response.headers['Content-Type'] = "text/xml"
        response  = "<?xml version='1.0' encoding='UTF-8'?>\n"
        response += "<Response>\n";
        if From in whitelist.keys():
            if debug: log("phone", From, "is in whitelist")
            response += "   <Dial timeout='"+timeout+"' action='record' method='GET'>"+home+"</Dial>\n"
        elif From in blacklist.keys():
            if debug: log("phone", From, "is in blacklist")
            response += "   <Reject reason='busy' />\n"
        else:
            if debug: log("phone", From, "is unknown")
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
        if debug: log("phone", "recording voicemail from", From)
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
               RecordingUrl, RecordingDuration, RecordingSid, Digits):
        if debug: log("phone", "received", RecordingDuration, "second voicemail from", From)
        
        # copy the file from Twilio's server and convert it to mp3
        twilioUrl = urllib.unquote(RecordingUrl)
        fileName = time.strftime("%Y%m%d%H%M%S")
        wavFile = fileName+".wav"
        mp3File = fileName+".mp3"
        command = "wget "+twilioUrl+" -O "+filePath+wavFile
        if debug: log("phone", "copying recording from", twilioUrl, "to", filePath+wavFile)
        os.system(command)
        command = "lame -b160 "+filePath+wavFile+" "+filePath+mp3File
        if debug: log("phone", "converting recording from", filePath+wavFile, "to", filePath+mp3File)
        os.system(command)
        command = "rm "+filePath+wavFile
        if debug: log("phone", "deleting", filePath+wavFile)
        os.system(command)
        
        # send the notification if it is longer than the minimum time
        if int(RecordingDuration) > minRecording:
            if debug: log("phone", "sending notification")
        
            # send the email announcing the voicemail
            subject = "New voicemail from "+phoneFmt(Caller)
            message  = "You have a new voicemail from "+phoneFmt(Caller)+"\n\n"
            message += "Click this link to listen to the message:\n"
            message += "http://"+urlPath+mp3File
            email(mailFrom, mailTo, subject, message)
        else:
            if debug: log("phone", "recording too short to send notification")

    # Retrieve a voicemail
    @cherrypy.expose
    def voicemail(self, vm):
        vmFile = open(filePath+vm)
        vMsg = vmFile.read()
        vmFile.close()
        cherrypy.response.headers['Content-Type'] = "audio/x-mp3"
        cherrypy.response.headers['Content-Range'] = "bytes 0-"+str(len(vMsg)-1)+"/"+str(len(vMsg))
        #cherrypy.response.headers['Content-Disposition'] = "attachment; filename='"+vm+"'"
        return vMsg
                
if __name__ == "__main__":

    # set up the web server
    baseDir = os.path.abspath(os.path.dirname(__file__))
    globalConfig = {
        'server.socket_port': webPort,
        'server.socket_host': "0.0.0.0",
        }
    appConfig = {
#        '/css': {
#            'tools.staticdir.on': True,
#            'tools.staticdir.root': os.path.join(baseDir, "static"),
#            'tools.staticdir.dir': "css",
#        },
#        '/js': {
#            'tools.staticdir.on': True,
#            'tools.staticdir.root': os.path.join(baseDir, "static"),
#            'tools.staticdir.dir': "js",
#        },
#        '/favicon.ico': {
#            'tools.staticfile.on': True,
#            'tools.staticfile.filename': os.path.join(baseDir, "static/favicon.ico"),
#        },
    }    
    cherrypy.config.update(globalConfig)
    root = WebRoot()
    cherrypy.tree.mount(root, "/", appConfig)
    access_log = cherrypy.log.access_log
    for handler in tuple(access_log.handlers):
        access_log.removeHandler(handler)
    cherrypy.engine.start()

