def test_module_inspect():
    import kidscompass.data as d
    print('module file:', getattr(d, '__file__', None))
    print('Database dir len:', len(dir(d.Database)))
    print('Database members:', dir(d.Database))
    assert True
