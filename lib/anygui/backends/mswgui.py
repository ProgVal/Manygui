from anygui.backends import *
#__all__ = anygui.__all__

__all__ = '''

  Application
  ButtonWrapper
  WindowWrapper
  LabelWrapper
  TextFieldWrapper
  TextAreaWrapper
  ListBoxWrapper
  FrameWrapper
  RadioButtonWrapper
  CheckBoxWrapper

'''.split()

from anygui.Utils import log
from anygui.Applications import AbstractApplication
from anygui.Wrappers import AbstractWrapper, DummyWidget, isDummy
from anygui.Events import *
from anygui import application

################################################################
import win32gui, win32con

# BUGS:
#
#    When I start test_listbox there is no way to control it
#    with the keyboard, even tabbing into the listbox.
#    Actually, it seems that the arrow keys don't work here
#    at all.

class ComponentWrapper(AbstractWrapper):
    # mixin class, implementing the backend methods
    #_height = -1 # -1 means default size in wxPython
    #_width = -1
    #_x = -1
    #_y = -1

    _win_style_ex = 0

    _hfont = win32gui.GetStockObject(win32con.ANSI_VAR_FONT)

    def __init__(self,*args,**kws):
        self._width = 0
        self._height = 0
        AbstractWrapper.__init__(self,*args,**kws)
        self.setConstraints('container','x','y','width','height',
                            'text','selection','geometry','visible')

    def widgetFactory(self,*args,**kws):
        app = application()
        if hasattr(self.proxy.container,'wrapper'):
            parent = self.proxy.container.wrapper.widget
        else:
            parent = 0
        widget = win32gui.CreateWindowEx(self._win_style_ex,
                                         self._wndclass,
                                         "",
                                         self._win_style,
                                         0,
                                         0,
                                         10,
                                         10,
                                         parent,
                                         0, # hMenu
                                         0, # hInstance
                                         None)
        app.widget_map[widget] = self
        return widget

    def widgetSetUp(self):
        self.proxy.container.wrapper.widget_map[self.widget] = self
        win32gui.SendMessage(self.widget,
                             win32con.WM_SETFONT,
                             self._hfont,
                             0)
        self.setVisible(1)

    def getGeometry(self):
        # Gag me with a cat.
        # Child window positions are reported relative to the
        # *toplevel* window, not relative to the parent.
        # Refactor this. - jak
        if isinstance(self,WindowWrapper):
            l,t,r,b = win32gui.GetClientRect(self.widget)
            w = r-l
            h = b-t
            return l,t,w,h

        l,t,r,b = win32gui.GetWindowRect(self.widget)
        w = r-l
        h = b-t

        if not isinstance(self.container.wrapper,WindowWrapper):
            try:
                if isinstance(self.proxy.container.wrapper,FrameWrapper):
                    px,py,pw,ph = self.proxy.container.geometry
                    l-=px
                    t-=py
                else:
                    done=1
            except AttributeError:
                pass

        return l,t,w,h

    def setX(self,x):
        if self.noWidget(): return
        ox,y,w,h = self.getGeometry()
        self.setGeometry(x,y,w,h)

    def setY(self,y):
        if self.noWidget(): return
        x,oy,w,h = self.getGeometry()
        self.setGeometry(x,y,w,h)

    def setWidth(self,width):
        if self.noWidget(): return
        x,y,ow,h = self.getGeometry()
        self.setGeometry(x,y,width,h)

    def setHeight(self,height):
        if self.noWidget(): return
        x,y,w,oh = self.getGeometry()
        self.setGeometry(x,y,w,height)

    def setSize(self,width,height):
        if self.noWidget(): return
        x,y,w,h = self.getGeometry()
        self.setGeometry(x,y,width,height)

    def setPosition(self,x,y):
        if self.noWidget(): return
        ox,oy,w,h = self.getGeometry()
        self.setGeometry(x,y,w,h)

    def setGeometry(self,x,y,width,height):
        if self.noWidget(): return
        win32gui.SetWindowPos(self.widget,
                              0,
                              x, y,
                              width, height,
                              win32con.SWP_NOACTIVATE | win32con.SWP_NOZORDER)

    def setVisible(self,visible):
        if self.noWidget(): return
        if visible:
            win32gui.ShowWindow(self.widget, win32con.SW_SHOWNORMAL)
        else:
            win32gui.ShowWindow(self.widget, win32con.SW_HIDE)

    def setEnabled(self,enabled):
        if self.noWidget(): return
        if enabled:
            win32gui.EnableWindow(self.widget, 1)
        else:
            win32gui.EnableWindow(self.widget, 0)

    def destroy(self):
        if self.proxy.container:
            try:
                del self.proxy.container.wrapper.widget_map[self.widget]
            except:
                pass
        if not self.noWidget():
            try:
                win32gui.DestroyWindow(self.widget)
            except:
                pass
            self.widget = DummyWidget()
                

    def setText(self,text):
        if self.noWidget(): return
        win32gui.SetWindowText(self.widget, str(text))

    def getText(self):
        return win32gui.GetWindowText(self.widget)

    def setContainer(self, container):
        if container is None:
            try:
                self.destroy()
            except:
                pass
            return
        parent = container.wrapper.widget
        try:
            assert parent.isDummy()
        except (AttributeError, AssertionError):
            self.destroy()
            self.create(parent)
            self.proxy.push(blocked=['container'])

    def enterMainLoop(self):
        self.proxy.push()


##################################################################

class LabelWrapper(ComponentWrapper):
    _wndclass = "STATIC"
    _win_style = win32con.SS_LEFT | win32con.WS_CHILD

##################################################################

class ButtonWrapper(ComponentWrapper):
    _wndclass = "BUTTON"
    _win_style = win32con.BS_PUSHBUTTON | win32con.WS_CHILD

    def _WM_COMMAND(self, hwnd, msg, wParam, lParam):
        #log("Button._WM_COMMAND called, looking for %s==%s"%(wParam>>16,win32con.BN_CLICKED))
        # lParam: handle of control (or NULL, if not from a control)
        # HIWORD(wParam): notification code
        # LOWORD(wParam): id of menu item, control, or accelerator
        if (wParam >> 16) == win32con.BN_CLICKED:
            #self.do_action()
            send(self.proxy, 'click')

##################################################################

class ListBoxWrapper(ComponentWrapper):
    _wndclass = "LISTBOX"
    _win_style = win32con.WS_CHILD | win32con.WS_VSCROLL | win32con.WS_BORDER | win32con.LBS_NOTIFY
    _win_style_ex = win32con.WS_EX_CLIENTEDGE

    def getSelection(self):
        if self.noWidget(): return
        return win32gui.SendMessage(self.widget,
                                    win32con.LB_GETCURSEL,
                                    0,
                                    0)

    def setItems(self,items):
        if self.noWidget(): return
        win32gui.SendMessage(self.widget,
                             win32con.LB_RESETCONTENT, 0, 0)
        for item in map(str, list(items)):
            # FIXME: This doesn't work! Items get jumbled...
            win32gui.SendMessage(self.widget,
                                 win32con.LB_ADDSTRING,
                                 0,
                                 item)
                

    def setSelection(self,selection):
        if self.noWidget(): return
        win32gui.SendMessage(self.widget,
                             win32con.LB_SETCURSEL,
                             selection, 0)

    def _WM_COMMAND(self, hwnd, msg, wParam, lParam):
        # lParam: handle of control (or NULL, if not from a control)
        # HIWORD(wParam): notification code
        # LOWORD(wParam): id of menu item, control, or accelerator
        if wParam >> 16 == win32con.LBN_SELCHANGE:
            #self.do_action()
            send(self.proxy, 'select')

##################################################################

class ToggleButtonWrapper(ComponentWrapper):

    def _WM_COMMAND(self, hwnd, msg, wParam, lParam):
        # lParam: handle of control (or NULL, if not from a control)
        # HIWORD(wParam): notification code
        # LOWORD(wParam): id of menu item, control, or accelerator
        if (wParam >> 16) == win32con.BN_CLICKED:
            #self.do_action()
            send(self.proxy, 'click')

    def setOn(self,on):
        if self.noWidget():
            return
        if on:
            val = win32con.BST_CHECKED
        else:
            val = win32con.BST_UNCHECKED
        win32gui.SendMessage(self.widget, win32con.BM_SETCHECK, val, 0)
        self._on = on

    def getOn(self):
        val = win32gui.SendMessage(self.widget, win32con.BM_GETSTATE, 0, 0)
        val = val & win32con.BST_CHECKED
        if val: return 1
        return 0

    def _WM_COMMAND(self, hwnd, msg, wParam, lParam):
        # lParam: handle of control (or NULL, if not from a control)
        # HIWORD(wParam): notification code
        # LOWORD(wParam): id of menu item, control, or accelerator
        if (wParam >> 16) != win32con.BN_CLICKED:
            return
        send(self.proxy, 'click')


class CheckBoxWrapper(ToggleButtonWrapper):
    _wndclass = "BUTTON"
    _win_style = win32con.BS_AUTOCHECKBOX | win32con.WS_CHILD


class RadioButtonWrapper(ToggleButtonWrapper):
    _wndclass = "BUTTON"
    _win_style = win32con.BS_AUTORADIOBUTTON | win32con.WS_CHILD

    def __init__(self,*args,**kws):
        self._value = -2
        ToggleButtonWrapper.__init__(self,*args,**kws)
    
    def widgetFactory(self,*args,**kws):
        # The first radiobutton in a group must have the wxRB_GROUP style
        if self.proxy.group and self.proxy.group._items.index(self.proxy) == 0:
            self._win_style |= win32con.WS_GROUP
        return ToggleButtonWrapper.widgetFactory(self,*args,**kws)

    def setGroup(self,group):
        if group == None:
            return
        if self.proxy not in group._items:
            group._items.append(self.proxy)

    def _WM_COMMAND(self, hwnd, msg, wParam, lParam):
        # lParam: handle of control (or NULL, if not from a control)
        # HIWORD(wParam): notification code
        # LOWORD(wParam): id of menu item, control, or accelerator
        if (wParam >> 16) != win32con.BN_CLICKED:
            return
        send(self.proxy, 'click')

##################################################################

### IMPORTANT NOTE: Until the 'copy-paste' structure has been
### fixed (e.g. with a common superclass), fixes in one of these
### text classes should probably also be done in the other.

##################################################################

# END COMMENT - search for JKJKJK

class TextFieldWrapper(ComponentWrapper):
    _wndclass = "EDIT"
    _win_style = win32con.ES_NOHIDESEL | win32con.ES_AUTOHSCROLL | \
                 win32con.WS_CHILD | win32con.WS_BORDER
    _win_style_ex = win32con.WS_EX_CLIENTEDGE

    def _to_native(self, text):
        return text.replace('\n', '\r\n')

    def _from_native(self, text):
        return text.replace('\r\n', '\n')

    def getText(self):
        if self.noWidget(): return
        return self._from_native(win32gui.GetWindowText(self.widget))

    def setText(self, text):
        if self.noWidget(): return
        if text == self.getText(): return
        win32gui.SetWindowText(self.widget, self._to_native(text))

    def getSelection(self):
        #log("TextField._backend_selection")
        if self.noWidget(): return
        result = win32gui.SendMessage(self.widget,
                                      win32con.EM_GETSEL,
                                      0, 0)
        start, end = result & 0xFFFF, result >> 16
        #log("    start,end=%s,%s"%(start,end))
        # under windows, the natice widget contains
        # CRLF line separators
        text = self.getText()
        start -= text[:start].count('\n')
        end -= text[:end].count('\n')
        return start, end
            
    def setSelection(self,selection):
        #log("TextField._ensure_selection")
        if self.noWidget(): return
        start, end = selection
        text = self.getText()
        start += text[:start].count('\n')
        end += text[:end].count('\n')
        #log("    start,end=%s,%s"%(start,end))
        win32gui.SendMessage(self.widget,
                             win32con.EM_SETSEL,
                             start, end)

    def setEditable(self,editable):
        if self.noWidget(): return
        if editable:
            win32gui.SendMessage(self.widget,
                                 win32con.EM_SETREADONLY,
                                 0, 0)
        else:
            win32gui.SendMessage(self.widget,
                                 win32con.EM_SETREADONLY,
                                 1, 0)

##    def _ensure_events(self):
##        if self.widget:
##            EVT_TEXT_ENTER(self.widget, self._msw_id, self._msw_enterkey)

##    def _msw_enterkey(self, event):
##        self.do_action()

    def _WM_COMMAND(self, hwnd, msg, wParam, lParam):
        pass

# FIXME: Inheriting TextField overrides TextArea defaults.
#        This is a temporary fix. (mlh20011222)
class TextAreaWrapper(TextFieldWrapper):
    _win_style = TextFieldWrapper._win_style | win32con.ES_MULTILINE | \
                 win32con.ES_AUTOVSCROLL | win32con.ES_WANTRETURN


class ContainerMixin:
    def __init__(self,*args,**kws):
        self.widget_map = {} # maps child window handles to instances
    
    def _WM_COMMAND(self, hwnd, msg, wParam, lParam):
        #log("ContainerMixin _WM_COMMAND called for %s"%self)
        # lParam: handle of control (or NULL, if not from a control)
        # HIWORD(wParam): notification code
        # LOWORD(wParam): id of menu item, control, or accelerator
        app = application()
        try:
            child_window = self.widget_map[lParam]
        except KeyError:
            #log("NO SUCH CHILD WINDOW %s"%lParam)
            # we receive (when running test_textfield.py)
            # EN_CHANGE (0x300) and EN_UPDATE (0x400) notifications
            # here even before the call to CreateWindow returns.
            return
        #log("Dispatching to child %s"%child_window)
        child_window._WM_COMMAND(hwnd, msg, wParam, lParam)

class FrameWrapper(ComponentWrapper,ContainerMixin):
    _win_style = win32con.WS_CHILD
    _win_style_ex = 0
    _wndclass = None

    def __init__(self,*args,**kws):
        ContainerMixin.__init__(self)
        ComponentWrapper.__init__(self,*args,**kws)


    def setContainer(self, *args, **kws):
        """
        OK, this probably needs to be pulled into a mixin heritable by
        various backends.
        
        Ensure all contents are properly created. This looks like it could
        be handled at the Proxy level, but it probably *shouldn't* be -
        it's handling a Tk-specific requirement about the order in which
        widgets must be created. (I did it the Proxy way too. This way
        is definitely "the simplest thing that could possibly work.") - jak
        """
        ComponentWrapper.setContainer(self, *args, **kws)
        for component in self.proxy.contents:
            component.container = self.proxy

    def _WM_SIZE(self, hwnd, msg, wParam, lParam):
        # Proxy handles resizing.
        pass

class WindowWrapper(ContainerMixin,ComponentWrapper):

    _win_style = win32con.WS_OVERLAPPEDWINDOW | win32con.WS_CLIPCHILDREN
    _win_style_ex = 0

    def __init__(self,*args,**kws):
        ComponentWrapper.__init__(self,*args,**kws)
        self.widget_map = {}

    def setGeometry(self,x,y,width,height):
        if self.noWidget(): return
        # take account for title bar and borders
        import win32api
        win32gui.SetWindowPos(self.widget,
                              0,
                              x, y,
                              width \
                              + 2*win32api.GetSystemMetrics(win32con.SM_CXFRAME),
                              height \
                              + win32api.GetSystemMetrics(win32con.SM_CYCAPTION) \
                              + 2*win32api.GetSystemMetrics(win32con.SM_CYFRAME),
                              win32con.SWP_NOACTIVATE | win32con.SWP_NOZORDER)

    def setContainer(self,container):
        if not application().isRunning(): return
        if container is None: return
        if self.noWidget():
            self.create()
        win32gui.ShowWindow(self.widget, win32con.SW_HIDE)
        win32gui.UpdateWindow(self.widget)
        self.proxy.push(blocked=['container'])
        # Ensure contents are properly created.
        for comp in self.proxy.contents:
            comp.container = self.proxy

    def setTitle(self,title):
        if self.noWidget(): return
        win32gui.SetWindowText(self.widget, title)

    def getTitle(self):
        win32gui.GetWindowText(self.widget, title)

    def widgetSetUp(self):
        Application.widget_map[self.widget] = self
        win32gui.SendMessage(self.widget,
                             win32con.WM_SETFONT,
                             self._hfont,
                             0)
    def _WM_SIZE(self, hwnd, msg, wParam, lParam):
        w, h = lParam & 0xFFFF, lParam >> 16
        if self._width==0 and self._height==0:
            # This will be the case when the widget is first
            # created. We need to ensure the contents get
            # reasonable geometries before we start sliding
            # them around, so ignore the initial resize.
            dw=0
            dh=0
        else:
            dw = w - self._width
            dh = h - self._height
        
        self._width = w
        self._height = h
        if (dw,dh) == (0,0): return
        self.proxy.resized(dw,dh)

    def _WM_CLOSE(self, hwnd, msg, wParam, lParam):
        self.destroy()
        application().remove(self.proxy)
        return 1

################################################################

class Application(AbstractApplication):
    widget_map = {} # maps top level window handles to window instances
    _wndclass = None

    def __init__(self):
        AbstractApplication.__init__(self)
        if not self._wndclass:
            self._register_class()
        WindowWrapper._wndclass = self._wndclass
        FrameWrapper._wndclass = self._wndclass
        global _app
        _app = self

    def _register_class(self):
        # register a window class for toplevel windows.
        wndclass = win32gui.WNDCLASS()
        wndclass.hbrBackground = win32con.COLOR_BTNFACE + 1
        wndclass.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        wndclass.hIcon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)
        wndclass.lpszClassName = "msw.anygui.PythonWindow"
        wndclass.lpfnWndProc = self._wndproc
        self.__class__._wndclass = win32gui.RegisterClass(wndclass)

    def _wndproc(self, hwnd, msg, wParam, lParam):
        #log("_wndproc called with %s,%s,%s,%s"%(hwnd,msg,wParam,lParam))
        try:
            window = self.widget_map[hwnd]
        except:
            #log("NO WINDOW TO DISPATCH???")
            return win32gui.DefWindowProc(hwnd, msg, wParam, lParam)
        # there should probably be a better way to dispatch messages
        if msg == win32con.WM_DESTROY:
            app = application()
            app.remove(window)
            if not app._windows:
                win32gui.PostQuitMessage(0)
        if msg == win32con.WM_CLOSE:
            return window._WM_CLOSE(hwnd, msg, wParam, lParam)
        if msg == win32con.WM_SIZE:
            return window._WM_SIZE(hwnd, msg, wParam, lParam)
        if msg == win32con.WM_COMMAND:
            #log("Dispatching command to %s"%window)
            return window._WM_COMMAND(hwnd, msg, wParam, lParam)
        return win32gui.DefWindowProc(hwnd, msg, wParam, lParam)
        
    def internalRun(self):
        win32gui.PumpMessages()

    def internalRemove(self):
        if not self._windows:
            win32gui.PostQuitMessage(0)

################################################################

# FIXME: Part of temporary fix earlier in file. (Search for xyzzy42)
#del anygui.Defaults # Imported earlier

if __name__ == '__main__':
    from anygui import *

    app = Application()
    win = Window(title = "A Standard Window",
                 width = 300, height = 200)
    win.show()
    application().run()
