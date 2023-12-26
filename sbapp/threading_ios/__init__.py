          
#
# threading_ios/__init__.py
# import support for threading replacement using Kivy and KivySwiftLink
# Use Swift dispatch on PSL instead of python threads

from threading_wrap import ThreadingSwift
#import ThreadingSwift

#class ThreadInternal:
#    name = "Thread"

#Thread = ThreadInternal()

###thread_swift = Threading().shared
thread_swift = ThreadingSwift()
#thread_swift = None
threads_local = dict()

class DataModel:

    def do_thread(self, thread_id):
        #print(message)
        # lookup the thread work function and call it
        threads_local[ thread_id ]

data_model = DataModel()

###thread_swift.py_callback = data_model

class ThreadObj:
    thread_ref = 0
    
    def __init__(self,group=None, target=None, daemon=None):
        ThreadObj.thread_ref += 1
        self.group=group
        self.target=target
        self.daemon=daemon
        self.thread_id = ThreadObj.thread_ref
        self.Lock = None

        #threads_local.append(self)
        
    def setDaemon(self, state ):
        self.state=state
        name = 'Set'
    def start(self):
        self.start=True
        thread_swift.thread_start(self.thread_id)
        
    def run_thread(self):
        print("runMe")
        
    #def Lock(self):
    #    pass

    #def _shutdown(self):
    #    print("shutdown")
        

def Thread(group = None, target = None, daemon = None):
    myThread = ThreadObj(group, target, daemon)
    name = "Thread"
    myThread.Lock = RLock()
    print(target)
    #print('Name ', name, ' group: ', group, ' target: ' target)
    threads_local[ myThread.thread_id ] = target
    return myThread
    
#def setDaemon(state ):
#    name = 'Set'

#def Lock():
#    pass
class Lock: 
    def acquire(self):
        pass
    def release(self):
        pass
class RLock: 
    def acquire(self):
        pass
    def release(self):
        pass


#def RLock():
#    pass

#RLock = [None]

