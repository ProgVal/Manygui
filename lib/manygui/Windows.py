from manygui import application, Defaults
from manygui.Frames import Frame
from manygui import backendModule

class Window(Frame, Defaults.Window):

    def __init__(self, *args, **kw):
        Frame.__init__(self, *args, **kw)
        Defaults.shift_window()

    def wrapperFactory(self):
        return backendModule().WindowWrapper(self)
    
    def destroy(self):
        Frame.destroy(self)
        try:
            application().remove(self)
        except ValueError:
            # Already removed
            pass

    def addMenu(self,menu):
        self.menu = menu
        if menu:
            menu.container = self
