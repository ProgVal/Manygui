"Mixins: mix-in classes for the anygui package"

from Exceptions import SetAttributeError, GetAttributeError, UnimplementedMethod, InternalError
from Events import link, send

'''
# One key responsibility of class Mixins.Attrib is dealing with
# methods called set* in backend wrappers.

# pairwise order constraints on _ensure_* method calls
_setter_order = (
    ('setText', 'setSelection'),
    )

# get all names of methods starting with "set" for a class & its
# bases. The names are ordered to respect all pairwise constraints
# (before, after) in sequence-of-pairs klass._setter_order, if any,
# defaulting to the global ones in this module's _setter_order
# variable

def _get_all_setters_helper(klass, theset):
    """ recursively get all methods in klass and bases named set* """
    for name in dir(klass):
        if name.startswith('set'):
            value = getattr(klass, name)
            if callable(value): theset[name]=1
    for base in klass.__bases__: _get_all_setters_helper(base, theset)

def _get_all_setters(klass):
    """ get all methods in klass and its bases named set*, sorted """
    setterset = {}
    _get_all_setters_helper(klass, setterset)
    constraints = getattr(klass, '_setter_order', _setter_order)
    setter_names = setterset.keys()
    setter_names.sort()
    return topological_sort(setter_names, constraints)

def topological_sort(items, constraints):
    """ topological sort (stable) of list 'items' to respect pairwise
        constraints coded as pairs (before, after) in sequence 'constraints'
    """
    # prepare mappings 'followers' [item -> set of items that must follow it]
    # and 'nleaders' [item -> number of items that must precede it]
    followers = {}
    nleaders = {}
    for before, after in constraints:
        if before in items and after in items:
            these_followers = followers.setdefault(before,{})
            if not these_followers.has_key(after):
                nleaders[after] = 1 + nleaders.get(after, 0)
                these_followers[after] = before
    # while there are items, pick one with no leaders, append it
    # to result, update list 'items' and mapping 'nleaders'
    result = []
    while items:
        # find first item left that has no 'leaders'
        for item in items:
            if nleaders.get(item,0)==0: break
        else:
            raise InternalError(items,"dependency loop")
        # move the item from 'items' to 'result'
        items.remove(item)
        result.append(item)
        # update the mapping 'nleaders'
        for follower in followers.get(item,{}).keys():
            nleaders[follower] -= 1
    return result
'''

class Attrib:
    """Attrib: mix-in class to support attribute getting & setting.


    Each attribute name may have a setter method _set_name and/or a getter
    method _get_name.  If only the latter, it's a read-only attribute.  If
    no _set_name, attribute is set directly in self.__dict__.  This only
    applies to attribute-names that do NOT start with '_'.

    If the value being set exposes a method .assigned, it's called just
    after the attribute assignment; if the previously-set value exposes
    a method .removed, it's called just before the attribute assignment.
    This supports Models as values for widget attributes.

    Besides __setattr__ and __getattr__ special methods with this
    functionality, Attrib supplies a set method to set many attributes
    and options, and an __init__ with similar functionality.  __init__
    also handles attributes listed in self.explicit_attributes.

    Another, similar feature of class Attrib: it supplies a modattr method
    that tries to change an attribute's value in-place, if feasible, rather
    than re-bind it.  Changing in-place means trying _modify_name (rather
    than _set_name), assigning to self.name[:], and assigning to
    self.name.value.  In the end, self.name is re-bound if in-place
    modification fails.  If the value being changed exposes a method
    .modified, it's called just after an in-place modification succeeds.

    Method modify has the same interface as set (to modify potentially
    more than one attribute at once) but uses modattr rather than setattr.

    # REWRITE:
    Attrib also supplies a default refresh method, which calls all the
    relevant methods named set* in the connected _dependant object if
    flag _inhibit_refresh is false.  In this release, all set* are
    called; eventually, some kind of mechanism will use the hints to
    be more selective/optimizing.  Attrib's responsibilities include
    enforcing a calling order among set* methods.


    Note that Attrib embodies two patterns (attribute setting/getting
    and refresh functionality) and is thus "Alexandrian dense"; cfr
    Vlissides, "Pattern Hatching", page 30, for pluses and minuses of
    such "dense" approaches and the resulting "profound" code.
    """

    _dependant = None
    #_all_setters = []           # no set* called until Attrib.__init__
    _inhibit_refresh = 0        # default Attribs are always refresh-enabled

    def __setattr__(self, name, value):
        if name[0]!='_':
            try:
                setter = getattr(self, "_set_"+name)
            except AttributeError:
                if hasattr(self, "_get_"+name):
                    raise SetAttributeError(self, name)
            else:
                try: getattr(self, name).removed(self, name)
                except: pass
                inhibit_refresh = setter(value)
                try: value.assigned(self, name)
                except: pass
                if not inhibit_refresh: self.refresh(assigned=name)
                return
        self.__dict__[name] = value
        if name[0]!='_':
            self.refresh(assigned=name)

    def __getattr__(self, name):
        if name[0]=='_': raise GetAttributeError(self, name)
        try:
            getter = getattr(self, "_get_"+name)
        except AttributeError:
            raise GetAttributeError(self, name)
        else:
            return getter()

    def _set_or_mod(self, func, *args, **kwds):
        for opt in args:
            # kwds.update(opt.__dict__) # Doesn't work in Jython 2.1a1
            for key, val in opt.__dict__.items():
                kwds[key] = val
        for name, value in kwds.items():
            func(self, name, value)

    def set(self, *args, **kwds):
        return self._set_or_mod(setattr, *args, **kwds)

    def modify(self, *args, **kwds):
        return self._set_or_mod(self.__class__.modattr, *args, **kwds)

    def modattr(self, name, value):
        if name[0]!='_':
            try: modifier = getattr(self, '_modify_'+name)
            except AttributeError: pass
            else:
                # found a modifier-method, delegate the task to it
                inhibit_update = modifier(value)
                try: getattr(self, name).modified()
                except: pass
                if not inhibit_update: self.refresh(modified=name)
                return

        # we need to perform the modification-task directly
        old_value = getattr(self, name, None)
        # try assigning to the "all-object slice"
        try: old_value[:] = value
        except:
            # try assigning to the "value" attribute of the old-value
            try: old_value.value = value
            except:
                # no in-place mod, so, just set it (bind or re-bind)
                setattr(self, name, value)
                return
        # in-place modification has succeeded, alert the old_value (if
        # it supplies a suitable method) and any watchers of 'self'
        try: old_value.modified()
        except: pass
        if name[0]!='_':
            self.refresh(modified=name)

    def __init__(self, *args, **kwds):
        # _all_setters must be computed exactly once per concrete class
        #if self._dependant is not None:
        #    klass = self._dependant.__class__
        #    if not klass.__dict__.has_key('_all_setters'):
        #        klass.__dict__['_all_setters'] = _get_all_setters(klass)

        """
        # handle explicit-attributes -- currently [pre 0.1 beta] disabled
        # (breaks some top-level window geometry/sizing in tkgui [?])
        try: explicit_attributes_names = self.explicit_attributes
        except AttributeError: pass
        else:
            for internal_name in explicit_attributes_names:
                external_name = internal_name[1:]
                if not kwds.has_key(external_name):
                    kwds[external_name] = getattr(self, internal_name)
        """

        self.set(*args, **kwds)

    def refresh(self, **ignore_kw):
        if self._inhibit_refresh: return
        # Temporary hack:
        attributes = [name for name in dir(self) if name[0] == '_']
        state = {}
        for name in attributes:
            state[name] = getattr(self, name)
        self._dependant.set(**state)
        #for setter_name in self._all_setters:
        #    getattr(self, ensure_name)()


class DefaultEventMixin:

    def __init__(self):
        if hasattr(self, '_default_event'):
            link(self, self._default_event, self._default_event_handler,
                 weak=1, loop=1)

    def _default_event_handler(self, event, source, **kw):
        send(self, 'default', **kw)
