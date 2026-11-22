"""Guest Linux-only window capture and input for reproducible RViz GUI checks.

Uses X11/XTest on the existing Ubuntu desktop. It never injects ROS goals itself.
"""
import argparse
import ctypes as C
import ctypes.util
import json
from pathlib import Path
import sys
import time

class Desktop:
    def __init__(self):
        self.x=C.CDLL(ctypes.util.find_library('X11'))
        self.x.XOpenDisplay.argtypes=[C.c_char_p];self.x.XOpenDisplay.restype=C.c_void_p
        self.display=self.x.XOpenDisplay(None)
        if not self.display:raise RuntimeError('Existing X11 desktop is not available')
        self.x.XDefaultRootWindow.argtypes=[C.c_void_p];self.x.XDefaultRootWindow.restype=C.c_ulong
        self.root=self.x.XDefaultRootWindow(self.display)
        self.x.XQueryTree.argtypes=[C.c_void_p,C.c_ulong,C.POINTER(C.c_ulong),C.POINTER(C.c_ulong),C.POINTER(C.POINTER(C.c_ulong)),C.POINTER(C.c_uint)]
        self.x.XFetchName.argtypes=[C.c_void_p,C.c_ulong,C.POINTER(C.c_char_p)]
        self.x.XFree.argtypes=[C.c_void_p]
        self.x.XSync.argtypes=[C.c_void_p,C.c_int]
        self.x.XRaiseWindow.argtypes=[C.c_void_p,C.c_ulong]
        self.x.XSetInputFocus.argtypes=[C.c_void_p,C.c_ulong,C.c_int,C.c_ulong]
        self.x.XGetGeometry.argtypes=[C.c_void_p,C.c_ulong,C.POINTER(C.c_ulong),C.POINTER(C.c_int),C.POINTER(C.c_int),C.POINTER(C.c_uint),C.POINTER(C.c_uint),C.POINTER(C.c_uint),C.POINTER(C.c_uint)]
        self.x.XTranslateCoordinates.argtypes=[C.c_void_p,C.c_ulong,C.c_ulong,C.c_int,C.c_int,C.POINTER(C.c_int),C.POINTER(C.c_int),C.POINTER(C.c_ulong)]
        # Windows can disappear between enumeration and querying.
        self.handler=C.CFUNCTYPE(C.c_int,C.c_void_p,C.c_void_p)(lambda *_:0)
        self.x.XSetErrorHandler.argtypes=[C.c_void_p];self.x.XSetErrorHandler(self.handler)
    def find(self,title):
        pending=[self.root];matches=[]
        for _ in range(10000):
            if not pending:break
            window=pending.pop();name=C.c_char_p()
            if self.x.XFetchName(self.display,window,C.byref(name)) and name.value:
                value=name.value.decode('utf-8',errors='replace');self.x.XFree(name)
                if title.casefold() in value.casefold():
                    geometry=self.geometry(window)
                    if geometry['width']>=300 and geometry['height']>=200:matches.append((window,value))
            root,parent=C.c_ulong(),C.c_ulong();children=C.POINTER(C.c_ulong)();count=C.c_uint()
            if self.x.XQueryTree(self.display,window,C.byref(root),C.byref(parent),C.byref(children),C.byref(count)):
                if children:
                    pending.extend(children[i] for i in range(count.value));self.x.XFree(children)
        if len(matches)!=1:raise RuntimeError('Expected one application window: '+str(matches))
        return matches[0]
    def geometry(self,window):
        root=C.c_ulong();x,y=C.c_int(),C.c_int();width,height,border,depth=C.c_uint(),C.c_uint(),C.c_uint(),C.c_uint()
        assert self.x.XGetGeometry(self.display,window,C.byref(root),C.byref(x),C.byref(y),C.byref(width),C.byref(height),C.byref(border),C.byref(depth))
        child=C.c_ulong();rx,ry=C.c_int(),C.c_int()
        self.x.XTranslateCoordinates(self.display,window,self.root,0,0,C.byref(rx),C.byref(ry),C.byref(child))
        return dict(x=rx.value,y=ry.value,width=width.value,height=height.value)
    def input(self,window,key=None,drag=None):
        xt=C.CDLL(ctypes.util.find_library('Xtst'))
        xt.XTestFakeMotionEvent.argtypes=[C.c_void_p,C.c_int,C.c_int,C.c_int,C.c_ulong]
        xt.XTestFakeButtonEvent.argtypes=[C.c_void_p,C.c_uint,C.c_int,C.c_ulong]
        xt.XTestFakeKeyEvent.argtypes=[C.c_void_p,C.c_uint,C.c_int,C.c_ulong]
        self.x.XStringToKeysym.argtypes=[C.c_char_p];self.x.XStringToKeysym.restype=C.c_ulong
        self.x.XKeysymToKeycode.argtypes=[C.c_void_p,C.c_ulong];self.x.XKeysymToKeycode.restype=C.c_uint
        self.x.XRaiseWindow(self.display,window);self.x.XSetInputFocus(self.display,window,1,0);self.x.XSync(self.display,0)
        if key:
            code=self.x.XKeysymToKeycode(self.display,self.x.XStringToKeysym(key.encode()))
            if not code:raise ValueError('Unknown X11 key')
            xt.XTestFakeKeyEvent(self.display,code,1,0);xt.XTestFakeKeyEvent(self.display,code,0,0)
        if drag:
            geometry=self.geometry(window);x,y,endx,endy=drag
            if not all(0<=v<limit for v,limit in zip(drag,[geometry['width'],geometry['height']]*2)):raise ValueError('Drag outside selected window')
            xt.XTestFakeMotionEvent(self.display,-1,geometry['x']+x,geometry['y']+y,0)
            xt.XTestFakeButtonEvent(self.display,1,1,0)
            self.x.XSync(self.display,0);time.sleep(.15)
            xt.XTestFakeMotionEvent(self.display,-1,geometry['x']+endx,geometry['y']+endy,0)
            xt.XTestFakeButtonEvent(self.display,1,0,0)
        self.x.XSync(self.display,0)

def main():
    p=argparse.ArgumentParser();p.add_argument('--title',default='RViz');p.add_argument('--out',type=Path,required=True)
    p.add_argument('--key');p.add_argument('--drag');a=p.parse_args()
    desktop=Desktop();window,title=desktop.find(a.title)
    if a.key or a.drag:desktop.input(window,a.key,list(map(int,a.drag.split(','))) if a.drag else None);time.sleep(.5)
    from PyQt5.QtWidgets import QApplication
    app=QApplication(sys.argv[:1]);screen=app.primaryScreen();geometry=desktop.geometry(window)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    screen.grabWindow(window).save(str(a.out))
    screen.grabWindow(desktop.root,geometry['x'],geometry['y'],geometry['width'],geometry['height']).save(str(a.out.with_name(a.out.stem+'_composited.png')))
    record=dict(window_id=window,title=title,geometry=geometry,input=dict(key=a.key,drag=a.drag),
                source='Actual guest X11 application window; no synthetic ROS visualization')
    a.out.with_suffix('.json').write_text(json.dumps(record,indent=2));print(json.dumps(record))

if __name__=='__main__':main()
