
def jam_sequence(*arguments):

    def jam_decorator(cls):

        def innermost_enclosed_sequence(self, left, right, *range_parameters):
            left_index = -1
            if not range_parameters:
                range_parameters = (0, len(self), 1)
            for right_index in range(*range_parameters):
                if self[right_index] == left:
                    left_index = right_index
                elif self[right_index] == right:
                    if left_index == -1:
                        continue
                    break
            else:
                return None
            return (left_index, right_index)

        setattr(cls, 'innermost_enclosed_sequence', innermost_enclosed_sequence)

        def outermost_enclosed_sequence(self, left, right, *range_parameters):
            if not range_parameters:
                range_parameters = (0, len(self), 1)
            left_index = -1
            level = 1
            for right_index in range(*range_parameters):
                if self[right_index] == left:
                    if left_index == -1:
                        left_index = right_index
                    else:
                        level += 1
                elif self[right_index] == right:
                    if left_index != -1:
                        level -= 1
                        if level == 0:
                            break
            else:
                return None
            return (left_index, right_index)

        setattr(cls, 'outermost_enclosed_sequence', outermost_enclosed_sequence)

        try:
            old_getitem = getattr(cls, '__getitem__')
            def new_getitem(self, key):
                result = old_getitem(self, key)
                if isinstance(key, slice):
                    result = cls(result)
                return result
            setattr(cls, '__getitem__', new_getitem)
        except AttributeError:
            pass

        def change_a(old_a):
            def new_a(self, arg):
                return cls(old_a(self, arg))
            return new_a

        for a in arguments:
            try:
                old_a = getattr(cls, a)
            except AttributeError:
                continue
            setattr(cls, a, change_a(old_a))

        return cls

    return jam_decorator

@jam_sequence('__add__', '__mul__', '__radd__', '__rmul__')
class JamList(list):
    pass
