from anygui import Window, ListBox, application

class SelectionPrinter(ListBox):

    def __init__(self, *arg, **kw):
        ListBox.__init__(self, *arg, **kw)
        self.action = self.print_selection

    def print_selection(self):
        print 'Item selected:', self.selection, '(%s)' % self.items[self.selection]

lb = SelectionPrinter()

lb.items = 'There was a wee cooper of county Fyfe, Nickety, nockety, noo, noo, noo'.split()
lb.selection = 2

win = Window(title='ListBox test', width=200, height=200)

win.place(lb, left=25, top=25, right=25, bottom=25,
          vstretch=1, hstretch=1)

win.show()

application().run()