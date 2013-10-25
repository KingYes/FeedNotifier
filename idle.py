import sys

if sys.platform == 'win32':
    from ctypes import *
    
    class LASTINPUTINFO(Structure):
        _fields_ = [
            ('cbSize', c_uint),
            ('dwTime', c_int),
        ]
        
    def get_idle_duration():
        lastInputInfo = LASTINPUTINFO()
        lastInputInfo.cbSize = sizeof(lastInputInfo)
        if windll.user32.GetLastInputInfo(byref(lastInputInfo)):
            millis = windll.kernel32.GetTickCount() - lastInputInfo.dwTime
            return millis / 1000.0
        else:
            return 0
if sys.platform == 'linux2':
    import ctypes
    import ctypes.util

    class XScreenSaverInfo(ctypes.Structure):
        _fields_ = [('window', ctypes.c_long),
                    ('state', ctypes.c_int),
                    ('kind', ctypes.c_int),
                    ('til_or_since', ctypes.c_ulong),
                    ('idle', ctypes.c_ulong),
                    ('eventMask', ctypes.c_ulong)]

    class IdleXScreenSaver(object):
        def __init__(self):
            self.xss = self._get_library('Xss')
            self.gdk = self._get_library('gdk-x11-2.0')

            self.gdk.gdk_display_get_default.restype = ctypes.c_void_p
            # GDK_DISPLAY_XDISPLAY expands to gdk_x11_display_get_xdisplay
            self.gdk.gdk_x11_display_get_xdisplay.restype = ctypes.c_void_p
            self.gdk.gdk_x11_display_get_xdisplay.argtypes = [ctypes.c_void_p]
            # GDK_ROOT_WINDOW expands to gdk_x11_get_default_root_xwindow
            self.gdk.gdk_x11_get_default_root_xwindow.restype = ctypes.c_void_p

            self.xss.XScreenSaverAllocInfo.restype = ctypes.POINTER(XScreenSaverInfo)
            self.xss.XScreenSaverQueryExtension.restype = ctypes.c_int
            self.xss.XScreenSaverQueryExtension.argtypes = [ctypes.c_void_p,
                                                            ctypes.POINTER(ctypes.c_int),
                                                            ctypes.POINTER(ctypes.c_int)]
            self.xss.XScreenSaverQueryInfo.restype = ctypes.c_int
            self.xss.XScreenSaverQueryInfo.argtypes = [ctypes.c_void_p,
                                                       ctypes.c_void_p,
                                                       ctypes.POINTER(XScreenSaverInfo)]

            event_base = ctypes.c_int()
            error_base = ctypes.c_int()
            gtk_display = self.gdk.gdk_display_get_default()
            self.dpy = self.gdk.gdk_x11_display_get_xdisplay(gtk_display)
            available = self.xss.XScreenSaverQueryExtension(self.dpy,
                                                            ctypes.byref(event_base),
                                                            ctypes.byref(error_base))
            if available == 1:
                self.xss_info = self.xss.XScreenSaverAllocInfo()
            else:
                self.xss_info = None

        def _get_library(self, libname):
            path = ctypes.util.find_library(libname)
            if not path:
                raise ImportError('Could not find library "%s"' % (libname, ))
            lib = ctypes.cdll.LoadLibrary(path)
            assert lib
            return lib

        def get_idle(self):
            if not self.xss_info:
                return 0

            # XScreenSaverQueryInfo(GDK_DISPLAY_XDISPLAY(gdk_display_get_default()),
            #                       GDK_ROOT_WINDOW(), mit_info);
            drawable = self.gdk.gdk_x11_get_default_root_xwindow()
            self.xss.XScreenSaverQueryInfo(self.dpy, drawable, self.xss_info)
            # return (mit_info->idle) / 1000;
            return self.xss_info.contents.idle / 1000

    idle_class = IdleXScreenSaver()

    def get_idle_duration():
        return idle_class.get_idle()
else:
    def get_idle_duration():
        return 0
        
if __name__ == '__main__':
    import time
    while True:
        duration = get_idle_duration()
        print 'User idle for %.2f seconds.' % duration
        time.sleep(1)
        