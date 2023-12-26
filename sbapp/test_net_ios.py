
import netifaces_ios

class testNetIos:

    class DataModel:
    
        def receive(self, message):
            print(message)

    def do_test(self):

        netIOS = NetifacesIOS()

        data_model = DataModel()

        netIOS.py_callback = data_model

        netIOS.send("hello from python !!!")
