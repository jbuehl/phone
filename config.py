debug = True

# white list of callers to pass through
whitelist = {
        "+18187486084":"Home phone",
        "+18182095530":"Joe cell",
	    "+18189129504":"Joe cell",
        "+18186419862":"Linda cell",
	    "+18188024334":"Linda cell",
        "+18182384524":"Linda work",
        "+18187203111":"Eric cell",
        "+18182377233":"Janet cell",
        "+18189958786":"Winnie home",
        "+18183706119":"Winnie cell",
        "+15105493429":"Kathy home",
        "+15106849801":"Kathy cell",
	    "+16785209916":"Darryl cell",
	    "+16505958678":"Cathy Bonnar home",
	    "+16502072808":"Cathy Bonnar cell",
	    "+14158657315":"Cathy Bonnar work",
	    "+18174417299":"Alex Hughes home",
	    "+18176889901":"Alex Hughes cell",
        "+18187691338":"Studio City Animal Hospital",
        "+18185080160":"Birkers",
	    "+12153681285":"Eddie Black",
	    "+18185228353":"David Israel",
	    "+18183966154":"Kaiser",
        "+18183735021":"Kaiser",
        	"+18183751785":"Kaiser",
        "+18184505668":"Kaiser",
        "+18002426422":"Amica",
    }

# black list of callers to immediately reject     
blacklist = {
        "+18182987829":"some woman speaking klingon",
	    "+17378742833":"mortgage refinance",
        "+19785702318":"mortgage refinance",
	    "+16613608325":"somebody in Saugus",
        "+15714311960":"Maritz Research",
        "+13023946876":"Ktech Service",
        "+10000000000":"spoofed"
    }

# configuration parameters
webPort = 3663
home = "+18187486084"             # home phone number
timeout = "30"                    # how long to ring the phone before going to voicemail
maxlength = "120"                 # maximum time to record a voicemail
mailFrom = "phone@thebuehls.com"
mailTo = "joe@thebuehls.com" # where to send email notifications to
filePath = "/root/voicemails/"   # absolute path of where to store voicemails
urlPath = "shadyglade.thebuehls.com:3663/voicemail?vm="                   # url path of where to retrieve voicemails
minRecording = 3                   # minimum size of a voicemail to pay attention to
recordingLanguage = "en-US"
#recordingLanguage = "sv-SE"
whitelistMessage = "Please leave a message." 
unknownMessage = """Please leave a message. Unless you are trying to sell us something or you have a political message, 
in which case, please hang up, remove this number from your list, and never call us again.  
But if you are someone we know, please leave a message and we will call you back as soon as we can."""
  
