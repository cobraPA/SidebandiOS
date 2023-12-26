#
# netifaces_ios/__init__.py
# import support for netifaces replacement using Kivy and KivySwiftLink

from netifaces_wrap import NetifacesSwift
#import netifaces_ios
#from netifaces_ios import *

#class netifaces_ios_swift:
#    def __init__(self):
#        self.interfaces = ["en0"]
#        print(" hi from netifaces_swift1 !!")
        
        
        
        
        
interfacesList = ["en0"]
# "provides no connectivity" interface skipped for Auto
#interfacesList = ["lo0"]
#interfacesList = ["en0","en2"]
# fails with no autointerface
#interfacesList = []
#ifaddressList = ["None"]
###print(" hi from netifaces_swift1 !!")


ios_net = NetifacesSwift()

ios_net.send(" netifaces_ios send python!!")
#ifaddressList = { 0: [] }
    
class DataModel:
    ifaddressList = { 0: [] }

    def receive(self, message):
        print(message)
    def receive2(self, message):
        interfacesList = message
        #print("!!!!!!receive2 going !!!!!")
        #for x in message:
        #    print(x)
    #def ifaddrCB(self, ifaddrDatfamily, ifaddrDatElem):
    #    print(ifAddrDatfamily)
    def ifaddrCBAdd(self, ifaddrFamily, ifaddrName, ifaddrAddr):
        #ifaddressList = { 0: []}
        ###print(" start ifaddressList ", self.ifaddressList )
        workdict= {"addr": ifaddrAddr, "name": ifaddrName}
        ##print(" workDict ", workdict )
        if ifaddrFamily in self.ifaddressList:
            # add new dict to existing List
            ifaddrDict = self.ifaddressList[ifaddrFamily]
            ##print( "working... append - ", ifaddrDict)
            add_it = True
            for currentAddr in ifaddrDict:
                if currentAddr["addr"] == ifaddrAddr:
                    # found it
                    add_it=False
            if add_it:
                ##print( "appending" )
                ifaddrDict.append(workdict)
                ##print( "append ", self.ifaddressList)
            ##else:
                ##print( "Not appending" )
        else:
            # List containing new dict
            ifaddrDict= [workdict]
            self.ifaddressList[ifaddrFamily] = ifaddrDict
            ##print(" create ", self.ifaddressList)

data_model = DataModel()

ios_net.py_callback = data_model

##netIOS.send("hello from python !!!")
ios_net.activeInterfaceNames()

AF_INET6 = ios_net.getAF_INET6()
AF_INET = ios_net.getAF_INET()
AF_LINK = ios_net.getAF_LINK()

def interfaces():
    return interfacesList
    
def ifaddresses(if_name):
    ios_net.gather(if_name)
    #return ios_net.py_callback.ifaddressList
    return data_model.ifaddressList
    #return ios_net.gather(if_name)
    
