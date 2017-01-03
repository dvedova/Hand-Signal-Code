import speech_recognition as sr
r = sr.Recognizer()
m = sr.Microphone()
def writeFile(path, contents): #from course website
    with open(path, "wt") as f:
        f.write(contents)
def readFile(path): #from course website
    with open(path, "rt") as f:
        return f.read()
def voiceRecognizer():
    #frame work form uberi speech_recognition github 
    #short little function which takes googles speech recognition api
    #and writes speech to a text file that the main progam can then read
    with m as source: r.adjust_for_ambient_noise(source)
    while True:
        print("say something!")
        with m as source: audio = r.listen(source)  
        print("processing...")
        try:
            # recognize speech using Google Speech Recognition
            value = r.recognize_google(audio)
            #writes the to the contact txt file (ex: contact right!!)
            writeFile('contact.txt',value)
            print("you said...")
            print(readFile('contact.txt')) 
        except sr.UnknownValueError:
            #dont crash on unrecognizeable speech
            print("didnt catch that")
            pass
        except sr.RequestError as e:
            print("not connected")
            #dont crash when not connected to the internet
            pass 
voiceRecognizer()
print(voiceRecognizer())