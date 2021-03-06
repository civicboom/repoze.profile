import unittest

class TestProfileMiddleware(unittest.TestCase):
    def _makeOne(self, *arg, **kw):
        from repoze.profile.profiler import AccumulatingProfileMiddleware
        return AccumulatingProfileMiddleware(*arg, **kw)
        

    def _makeEnviron(self, kw):
        environ = {}
        environ['wsgi.url_scheme'] = 'http'
        environ['CONTENT_TYPE'] = 'text/html'
        environ['QUERY_STRING'] = ''
        environ['SERVER_NAME'] = 'localhost'
        environ['SERVER_PORT'] = '80'
        environ['REQUEST_METHOD'] = 'POST'
        environ.update(kw)
        return environ

    def test_index_post(self):
        from StringIO import StringIO
        fields = [
            ('full_dirs', '1'),
            ('sort', 'cumulative'),
            ('limit', '500'),
            ('mode', 'callers'),
            ]
        content_type, body = encode_multipart_formdata(fields)
        environ = self._makeEnviron(
            {'wsgi.input':StringIO(body),
             'CONTENT_TYPE':content_type,
             'CONTENT_LENGTH':len(body),
             'REQUEST_METHOD':'POST',
             })
        middleware = self._makeOne(None)
        html = middleware.index(environ)
        self.failIf(html.find('There is not yet any profiling data') == -1)

    def test_index_get(self):
        environ = self._makeEnviron({
             'REQUEST_METHOD':'GET',
             'wsgi.input':'',
             })
        middleware = self._makeOne(None)
        html = middleware.index(environ)
        self.failIf(html.find('There is not yet any profiling data') == -1)

    def test_index_clear(self):
        import os
        from StringIO import StringIO
        import tempfile
        fields = [
            ('full_dirs', '1'),
            ('sort', 'cumulative'),
            ('limit', '500'),
            ('mode', 'callers'),
            ('clear', 'submit'),
            ]
        content_type, body = encode_multipart_formdata(fields)
        environ = self._makeEnviron(
            {'wsgi.input':StringIO(body),
            'CONTENT_TYPE':content_type,
             'CONTENT_LENGTH':len(body),
             'REQUEST_METHOD':'POST',
             })

        middleware = self._makeOne(None)
        f = tempfile.mktemp()
        open(f, 'w').write('x')
        middleware.log_filename = f
        html = middleware.index(environ)
        self.failIf(html.find('There is not yet any profiling data') == -1)
        self.failIf(os.path.exists(f))

    def test_index_get_withdata(self):
        from StringIO import StringIO
        environ = self._makeEnviron({
             'REQUEST_METHOD':'GET',
             'wsgi.input':'',
             })
        middleware = self._makeOne(None)
        output = StringIO('hello!')
        html = middleware.index(environ, output)
        self.failUnless('Profiling information is generated' in html)

    def test_index_post_withdata_full_dirs(self):
        from StringIO import StringIO
        fields = [
            ('full_dirs', '1'),
            ('sort', 'cumulative'),
            ('limit', '500'),
            ('mode', 'callers'),
            ]
        content_type, body = encode_multipart_formdata(fields)
        environ = self._makeEnviron(
            {'wsgi.input':StringIO(body),
            'CONTENT_TYPE':content_type,
             'CONTENT_LENGTH':len(body),
             })

        middleware = self._makeOne(None)
        environ['PATH_INFO'] = middleware.path
        middleware = self._makeOne(None)
        output = StringIO('hello!')
        html = middleware.index(environ, output)
        self.failUnless('Profiling information is generated' in html)

    def test_index_withstats(self):
        import os
        import tempfile
        from StringIO import StringIO
        fields = [
            ('sort', 'cumulative'),
            ('limit', '500'),
            ('mode', 'stats'),
            ]
        content_type, body = encode_multipart_formdata(fields)
        environ = self._makeEnviron(
            {'wsgi.input':StringIO(body),
            'CONTENT_TYPE':content_type,
             'CONTENT_LENGTH':len(body),
             })

        middleware = self._makeOne(None)
        stats = DummyStats()
        middleware.Stats = stats
        f = tempfile.mktemp()
        open(f, 'w').write('x')
        middleware.log_filename = f
        environ['PATH_INFO'] = middleware.path
        middleware.index(environ)
        self.assertEqual(stats.stripped, True)
        self.failIfEqual(stats.stream, True)
        self.assertEqual(stats.printlimit, 500)
        self.assertEqual(stats.sortspec, 'cumulative')
        os.remove(f)

    def test_app_iter_is_not_closed(self):
        middleware = self._makeOne(app)
        def start_response(status, headers, exc_info=None):
            pass
        environ = {}
        iterable = middleware(environ, start_response)
        self.assertEqual(iterable.closed, False)

    def test_app_iter_as_generator_is_consumed(self):
        _consumed = []
        def start_response(status, headers, exc_info=None):
            pass
        def _app(status, headers, exc_info=None):
            start_response('200 OK', (), exc_info)
            yield 'one'
            _consumed.append('OK')
        middleware = self._makeOne(_app)
        environ = {}
        iterable = middleware(environ, start_response)
        self.failUnless(_consumed)

    def test_call_withpath(self):
        from StringIO import StringIO
        fields = [
            ('full_dirs', '1'),
            ('sort', 'cumulative'),
            ('limit', '500'),
            ('mode', 'callers'),
            ]
        content_type, body = encode_multipart_formdata(fields)
        environ = self._makeEnviron(
            {'wsgi.input':StringIO(body),
            'CONTENT_TYPE':content_type,
             'CONTENT_LENGTH':len(body),
             })

        middleware = self._makeOne(None)
        environ['PATH_INFO'] = middleware.path
        statuses = []
        headerses = []
        def start_response(status, headers):
            statuses.append(status)
            headerses.append(headers)
        iterable = middleware(environ, start_response)
        html = iterable[0]
        self.failIf(html.find('There is not yet any profiling data') == -1)
        self.assertEqual(statuses[0], '200 OK')
        self.assertEqual(headerses[0][0], ('content-type', 'text/html'))
        self.assertEqual(headerses[0][1], ('content-length', str(len(html))))

    def test_call_discard_first_request(self):
        import os
        from StringIO import StringIO
        import tempfile
        fields = [
            ('full_dirs', '1'),
            ('sort', 'cumulative'),
            ('limit', '500'),
            ('mode', 'callers'),
            ]
        content_type, body = encode_multipart_formdata(fields)
        environ = self._makeEnviron(
            {'wsgi.input':StringIO(body),
            'CONTENT_TYPE':content_type,
             'CONTENT_LENGTH':len(body),
             })
        log_filename = tempfile.mktemp()
        middleware = self._makeOne(app, log_filename=log_filename)
        self.failUnless(middleware.first_request)
        statuses = []
        headerses = []
        def start_response(status, headers, exc_info=None):
            statuses.append(status)
            headerses.append(headers)
        middleware(environ, start_response)
        self.assertEqual(statuses[0], '200 OK')
        self.failIf(middleware.first_request)
        self.failIf(os.path.exists(log_filename))
        middleware(environ, start_response)
        self.failUnless(os.path.exists(log_filename))
        os.remove(log_filename)

    def test_call_keep_first_request(self):
        import os
        from StringIO import StringIO
        import tempfile
        fields = [
            ('full_dirs', '1'),
            ('sort', 'cumulative'),
            ('limit', '500'),
            ('mode', 'callers'),
            ]
        content_type, body = encode_multipart_formdata(fields)
        environ = self._makeEnviron(
            {'wsgi.input':StringIO(body),
            'CONTENT_TYPE':content_type,
             'CONTENT_LENGTH':len(body),
             })
        log_filename = tempfile.mktemp()
        middleware = self._makeOne(app, discard_first_request=False,
                                   log_filename=log_filename)
        self.failIf(middleware.first_request)
        statuses = []
        headerses = []
        def start_response(status, headers, exc_info=None):
            statuses.append(status)
            headerses.append(headers)
        middleware(environ, start_response)
        self.assertEqual(statuses[0], '200 OK')
        self.failIf(middleware.first_request)
        self.failUnless(os.path.exists(log_filename))
        os.remove(log_filename)

    def test_call_with_cachegrind(self):
        from repoze.profile.profiler import HAS_PP2CT
        if not HAS_PP2CT: # pragma: no cover
            return
        import os
        from StringIO import StringIO
        import tempfile
        fields = [
            ('full_dirs', '1'),
            ('sort', 'cumulative'),
            ('limit', '500'),
            ('mode', 'callers'),
            ]
        content_type, body = encode_multipart_formdata(fields)
        environ = self._makeEnviron(
            {'wsgi.input':StringIO(body),
            'CONTENT_TYPE':content_type,
             'CONTENT_LENGTH':len(body),
             })
        log_filename = tempfile.mktemp()
        cachegrind_filename = tempfile.mktemp()
        middleware = self._makeOne(app, discard_first_request=False,
                                   log_filename=log_filename,
                                   cachegrind_filename=cachegrind_filename)
        self.failIf(middleware.first_request)
        statuses = []
        headerses = []
        def start_response(status, headers, exc_info=None):
            statuses.append(status)
            headerses.append(headers)
        middleware(environ, start_response)
        self.assertEqual(statuses[0], '200 OK')
        self.failIf(middleware.first_request)
        self.failUnless(os.path.exists(log_filename))
        os.remove(log_filename)
        self.failUnless(os.path.exists(cachegrind_filename))
        os.remove(cachegrind_filename)

    def test_flush_at_shutdown(self):
        import os
        import tempfile
        fields = [
            ('full_dirs', '1'),
            ('sort', 'cumulative'),
            ('limit', '500'),
            ('mode', 'callers'),
            ]
        content_type, body = encode_multipart_formdata(fields)
        log_filename = tempfile.mktemp()
        middleware = self._makeOne(app, flush_at_shutdown=True,
                                   log_filename=log_filename)
        f = open(log_filename, 'w')
        f.write('')
        del middleware
        self.failIf(os.path.exists(log_filename))
        
    def test_keep_at_shutdown(self):
        import os
        import tempfile
        fields = [
            ('full_dirs', '1'),
            ('sort', 'cumulative'),
            ('limit', '500'),
            ('mode', 'callers'),
            ]
        content_type, body = encode_multipart_formdata(fields)
        log_filename = tempfile.mktemp()
        middleware = self._makeOne(app, flush_at_shutdown=False,
                                   log_filename=log_filename)
        f = open(log_filename, 'w')
        f.write('')
        del middleware
        self.failUnless(os.path.exists(log_filename))
        os.remove(log_filename)

class TestMakeProfileMiddleware(unittest.TestCase):
    def _callFUT(self, *arg, **kw):
        from repoze.profile.profiler import make_profile_middleware
        return make_profile_middleware(*arg, **kw)

    def test_it(self):
        mw = self._callFUT(app,
                           {},
                           log_filename='/tmp/log',
                           cachegrind_filename='/tmp/cachegrind',
                           discard_first_request='true',
                           flush_at_shutdown='false',
                           path='/__profile__')
        self.assertEqual(mw.app, app)
        self.assertEqual(mw.log_filename, '/tmp/log')
        self.assertEqual(mw.cachegrind_filename, '/tmp/cachegrind')
        self.assertEqual(mw.first_request, True)
        self.assertEqual(mw.flush_at_shutdown, False)
        self.assertEqual(mw.path, '/__profile__')
        
def app(environ, start_response, exc_info=None):
    start_response('200 OK', (), exc_info)
    return closeable([''])

class closeable(list):
    closed = False
    def close(self): self.closed = True

def encode_multipart_formdata(fields):
    BOUNDARY = '----------ThIs_Is_tHe_bouNdaRY_$'
    CRLF = '\r\n'
    L = []
    for (key, value) in fields:
        L.append('--' + BOUNDARY)
        L.append('Content-Disposition: form-data; name="%s"' % key)
        L.append('')
        L.append(value)
    L.append('--' + BOUNDARY + '--')
    L.append('')
    body = CRLF.join(L)
    content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
    return content_type, body

class DummyStats:
    stripped = False
    stream = True
    log_filename = None
    def __call__(self, log_filename):
        self.log_filename = log_filename
        return self

    def strip_dirs(self):
        self.stripped = True

    def print_stats(self, limit):
        self.printlimit = limit

    def sort_stats(self, sort):
        self.sortspec = sort
        


