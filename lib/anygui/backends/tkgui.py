
from anygui.backends import *
__all__ = anygui.__all__

################################################################

from Tkinter import * # A bit risky
import re, Tkinter

class ComponentMixin:
    # mixin class, implementing the backend methods
    # FIXME: Defaults...
    _height = -1
    _width = -1
    _x = -1
    _y = -1

    _tk_comp = None
    _tk_id = None
    _tk_style = 0
    
    def _is_created(self):
        return self._tk_comp is not None

    def _ensure_created(self):
        if self._tk_comp is None:
            if self._container is not None:
                parent = self._container._tk_comp
            else:
                parent = None
            frame = self._tk_class(parent
                                   #text=self._get_tk_text(),
                                   #style=self._tk_style
                                   )
            # FIXME: Should be handled by _ensure_title and _ensure_text
            if self._tk_class is not Toplevel: #?
                try:
                    frame.config(text=self._get_tk_text())
                except: # FIXME: Ugly... (ListBox etc. doesn't have a text property)
                    pass
                if self._tk_class is Tkinter.Label:
                    frame.config(justify=self._tk_style, anchor=W) # FIXME: anchor assumes LEFT
            else:
                frame.title(self._get_tk_text())
            self._tk_comp = frame
            return 1
        return 0

    def _ensure_events(self):
        pass

    def _ensure_geometry(self):
        if self._tk_comp:
            # FIXME: Does this work with windows?
            self._tk_comp.place(x=self._x, y=self._y,
                                width=self._width, height=self._height)

    def _ensure_visibility(self):
        if self._tk_comp:
            # FIXME: Hack...
            if self._visible:
                self._ensure_geometry()
            else:
                self._tk_comp.place_forget()

    def _ensure_enabled_state(self):
        if self._tk_comp:
            # FIXME: Ugly solution
            try:
                if self._enabled:
                    self._tk_comp.config(state=NORMAL)
                else:
                    self._tk_comp.config(state=DISABLED)
            except TclError:
                pass # Widget didn't support -state

    def _ensure_destroyed(self):
        if self._tk_comp:
            #self._tk_comp.Destroy()
            self._tk_comp = None

    def _get_tk_text(self):
        # helper function for creation
        # returns the text required for creation.
        # This may be the _text property, or _title, ...,
        # depending on the subclass
        return self._text

################################################################

class Label(ComponentMixin, AbstractLabel):
    _width = 100 # auto ?
    _height = 32 # auto ?
    _tk_class = Tkinter.Label
    _text = "tkLabel"
    _tk_style = LEFT

    def _ensure_text(self):
        if self._tk_comp:
            # FIXME: Wrong place for the style...
            # FIXME: anchor assumes LEFT
            self._tk_comp.config(text=self._text, justify=self._tk_style, anchor=W)

################################################################

class ListBox(ComponentMixin, AbstractListBox):
    _tk_class = Tkinter.Listbox

    def _backend_items(self):
        if self._tk_comp:
            return self._tk_comp.get(0, END)

    def _backend_selection(self):
        if self._tk_comp:
            selection = self._tk_comp.curselection()[0]
            try:
                selection = int(selection)
            except ValueError: pass
            return selection

    def _ensure_items(self):
        if self._tk_comp:
            self._tk_comp.delete(0, END)
            for item in self._items:
                self._tk_comp.insert(END, item)

    def _ensure_selection(self):
        if self._tk_comp:
            self._tk_comp.select_clear(self._selection)
            self._tk_comp.select_set(self._selection)

    def _ensure_events(self):
        if self._tk_comp:
            self._tk_comp.bind('<ButtonRelease-1>', self._tk_clicked)

    def _tk_clicked(self, event):
        self.do_action()

################################################################

class Button(ComponentMixin, AbstractButton):
    _tk_class = Button
    _text = "tkButton"

    def _ensure_events(self):
        if self._tk_comp:
            self._tk_comp.config(command=self._tk_clicked)

    def _tk_clicked(self):
        self.do_action()

class ToggleButtonMixin(ComponentMixin):

    def _ensure_state(self):
        if self._tk_comp is not None:
            self._var.set(self._on)

    def _ensure_created(self):
        ComponentMixin._ensure_created(self)
        self._var = IntVar()
        self._tk_comp.config(variable=self._var, anchor=W)
        return 1

    
    def _tk_clicked(self):
        val = self._var.get()
        if val == self._on:
            return
        self._on = val
        self.do_action()

class CheckBox(ToggleButtonMixin, AbstractCheckBox):
    _tk_class = Checkbutton
    _text = "tkCheckbuton"

    def _ensure_events(self):
        self._tk_comp.config(command=self._tk_clicked)

class RadioButton(ToggleButtonMixin, AbstractRadioButton):
    _tk_class = Radiobutton
    _text = "tkRadiobutton"

    def _ensure_created(self):
        result = ToggleButtonMixin._ensure_created(self)
        self._tk_comp.config(value=1) # FIXME: Shaky...
        return result

    def _ensure_events(self):
        self._tk_comp.config(command=self._tk_clicked)

################################################################

class TextField(ComponentMixin, AbstractTextField):
    _tk_class = Tkinter.Entry

    def _backend_text(self):
        if self._tk_comp:
            return self._tk_comp.get()

    def _backend_selection(self):
        if self._tk_comp:
            if self._tk_comp.select_present():
                start = self._tk_comp.index('sel.first')
                end = self._tk_comp.index('sel.last')
            else:
                start = end = self._tk_comp.index('insert')
            return start, end
            
    def _ensure_text(self):
        if self._tk_comp:
            self._tk_comp.delete(0, END)
            self._tk_comp.insert(0, self._text)

    def _ensure_selection(self):
        if self._tk_comp:
            start, end = self._selection
            self._tk_comp.selection_range(start, end)

    def _ensure_editable(self):
        if self._tk_comp:
            if self._editable:
                state = NORMAL
            else:
                state = DISABLED
            self._tk_comp.config(state=state)

    def _ensure_events(self):
        if self._tk_comp:
            self._tk_comp.bind('<KeyPress-Return>', self._tk_enterkey)

    def _tk_enterkey(self, event):
        self.do_action()

class ScrollableTextArea(Frame):

    # Replacemenent for Tkinter.Text

    def __init__(self, *args, **kw):
        Frame.__init__(self, *args, **kw)
        
        self._yscrollbar = Tkinter.Scrollbar(self)
        self._yscrollbar.pack(side=RIGHT, fill=Y)

        self._xscrollbar = Tkinter.Scrollbar(self, orient=HORIZONTAL)
        self._xscrollbar.pack(side=BOTTOM, fill=X)
        
        self._textarea = Tkinter.Text(self,
                                      yscrollcommand=self._yscrollbar.set,
                                      xscrollcommand=self._xscrollbar.set)
        self._textarea.pack(side=TOP, fill=BOTH)

        self._yscrollbar.config(command=self._textarea.yview)
        self._xscrollbar.config(command=self._textarea.xview)


    def config(self, **kw):
        self._textarea.config(**kw)

    def get(self, start, end):
        return self._textarea.get(start, end)

    def mark_names(self):
        return self._textarea.mark_names()

    def index(self, mark):
        return self._textarea.index(mark)

    def delete(self, start, end):
        self._textarea.delete(start, end)

    def insert(self, index, text):
        self._textarea.insert(index, text)

    def mark_set(self, mark, position):
        self._textarea.mark_set(mark, position)

    def tag_add(self, tag, start, end):
        self._textarea.tag_add(tag, start, end)

    def tag_remove(self, tag, start, end):
        self._textarea.tag_remove(tag, start, end)

    def tag_names(self): return self._textarea.tag_names()


# FIXME: 'Copy-Paste' inheritance...
class TextArea(ComponentMixin, AbstractTextArea):
    _tk_class = ScrollableTextArea # Tkinter.Text

    def _ensure_created(self):
        result = ComponentMixin._ensure_created(self)
        if result:
            self._tk_comp.config(wrap=NONE) #, wrap=WORD)
        return result

    def _backend_text(self):
        if self._tk_comp:
            return self._tk_comp.get(1.0, END)[:-1] # Remove the extra newline. (Always?)

    def _to_char_index(self,idx):
        # This is no fun, but there doesn't seem to be an easier way than
        # counting the characters in each line :-(   -- jak
        txt = self._tk_comp
        idx = txt.index(idx)
        line,col = idx.split(".")
        line=int(line)
        tlen = 0
        for ll in range(1,line):
            tlen += len(txt.get("%s.0"%ll,"%s.end"%ll))
            tlen += 1
        tlen += int(col)
        return tlen

    def _backend_selection(self):
        if self._tk_comp:
            try:
                start = self._tk_comp.index('sel.first')
                end = self._tk_comp.index('sel.last')
            except TclError:
                start = end = self._tk_comp.index('insert')
                # Convert to character positions...
            start = self._to_char_index(start)
            end = self._to_char_index(end)
            return start, end

    def _ensure_text(self):
        if self._tk_comp:
            self._tk_comp.config(state=NORMAL) # Make sure we can change the text
            self._tk_comp.delete(1.0, END)
            self._tk_comp.insert(1.0, self._text)
            self._ensure_editable() # Make the state is synched

    def _ensure_selection(self):
        if self._tk_comp:
            start, end = self._selection
            self._tk_comp.tag_remove('sel','1.0','end')
            self._tk_comp.tag_add('sel', '1.0 + %s char' % start, '1.0 + %s char' % end)

    def _ensure_editable(self):
        if self._tk_comp:
            if self._editable:
                state = NORMAL
            else:
                state = DISABLED
            self._tk_comp.config(state=state)

################################################################

class Window(ComponentMixin, AbstractWindow):

    _tk_class = Toplevel
    _tk_style = 0

    def _ensure_created(self):
        result = ComponentMixin._ensure_created(self)
        #if result:
        #    self._tk_comp.SetAutoLayout(1)
        return result

    def _ensure_visibility(self):
        if self._tk_comp:
            if self._visible:
                self._tk_comp.deiconify()
            else:
                self._tk_comp.withdraw()

    def _ensure_geometry(self):
        geometry = "%dx%d%+d%+d" % (self._width, self._height,
                                    #self._x, self._y)
                                    0, 0)
        if self._tk_comp:
            self._tk_comp.geometry(geometry)
    
    def _ensure_events(self):
        self._tk_comp.bind('<Configure>', self._tk_size_handler)
        self._tk_comp.protocol('WM_DELETE_WINDOW', self._tk_close_handler)

    def _ensure_title(self):
        if self._tk_comp:
            self._tk_comp.title(self._title)

    def _tk_close_handler(self):
        global _app
        self._tk_comp.destroy()
        self.destroy()
        _app._window_deleted()

    def _tk_size_handler(self, dummy):
        g = self._tk_comp.geometry()
        m = re.match('^(\d+)x(\d+)', g)
        w = int(m.group(1))
        h = int(m.group(2))
        dw = w - self._width
        dh = h - self._height
        self._width = w
        self._height = h
        self.resized(dw, dh)

    def _get_tk_text(self):
        return self._title

################################################################

class Application(AbstractApplication):
    def __init__(self):
        AbstractApplication.__init__(self)
        self._root = Tk()
        self._root.withdraw()
        # FIXME: Ugly...
        global _app
        _app = self

    def _window_deleted(self):
        if not self._windows:
            self._root.destroy()
    
    def _mainloop(self):
        self._root.mainloop()

################################################################

class factory:
    _map = {'Window': Window,
            'Button': Button,
            'RadioButton': RadioButton,
            'RadioGroup': RadioGroup,
            'CheckBox': CheckBox,
            'Application': Application,
            'Label': Label,
            'TextField': TextField,
            'TextArea': TextArea,
            'ListBox': ListBox,
            }
    def get_class(self, name):
        return self._map[name]
