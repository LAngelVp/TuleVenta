def _pyi_rthook():
    import inspect

    _original_getsource = inspect.getsource

    def _safe_getsource(obj):
        try:
            return _original_getsource(obj)
        except (AttributeError, OSError, TypeError):
            return ""

    inspect.getsource = _safe_getsource


_pyi_rthook()
del _pyi_rthook