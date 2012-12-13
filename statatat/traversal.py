#!/usr/bin/python
# -*- coding: utf-8 -*-
from hashlib import md5
import tw2.core as twc

import statatat.models
import statatat.widgets
import statatat.widgets.graph

import pyramid.threadlocal
import pyramid.security


def make_root(request):
    return RootApp(request)


class RootApp(dict):

    __name__ = None
    __parent__ = None

    def __init__(self, request):
        dict.__init__(self)
        self.request = request
        self.static = dict(webhooks=WebHookApp(), api=ApiApp(),
                           widget=WidgetApp())

        # TODO.. need some nice pattern for doing this "automatically"

        self.static['widget'].__parent__ = self

    def __getitem__(self, key):
        if key in self.static:
            return self.static[key]

        query = statatat.models.User.query.filter_by(username=key)
        if query.count() != 1:
            raise KeyError('No such user')

        # TODO -- definitely not the right way to be doing this.

        request = pyramid.threadlocal.get_current_request()
        username = pyramid.security.authenticated_userid(request)
        if username != key:
            raise KeyError('Not allowed')

        return UserApp(user=query.one())


# TODO - this whole thing needs cleaned up.  it contains cruft.

class WidgetApp(object):

    def __getitem__(self, key):
        query = statatat.models.User.query.filter_by(username=key)
        if query.count() != 1:
            return self.handle_floating()
        else:
            return self.handle_user(query)

    def handle_floating(self):
        backend_key = 'moksha.livesocket.backend'
        backend = self.__parent__.request.registry.settings[backend_key]

        return statatat.widgets.graph.make_sysinfo_chart(backend=backend,
                topic='sysinfo')

    def handle_user(self, query):

        # user = query.first()

        # Old github stuff..
        # salt = "TODO MAKE THIS SECRET"
        # topics = ",".join((
        #    "%s.%s" % ("author", md5(salt + email).hexdigest())
        #    for email in user.emails
        # ))

        backend_key = 'moksha.livesocket.backend'
        backend = self.__parent__.request.registry.settings[backend_key]

        return statatat.widgets.graph.make_chart(backend=backend)


class ApiApp(object):

    def __getitem__(self, key):
        query = statatat.models.User.query.filter_by(username=key)
        if query.count() != 1:
            raise KeyError('No such user')

        # TODO -- definitely not the right way to be doing this.

        request = pyramid.threadlocal.get_current_request()
        username = pyramid.security.authenticated_userid(request)
        if username != key:
            raise KeyError('Not allowed')

        return query.one()


class WebHookApp(object):

    pass


class UserApp(statatat.widgets.UserProfile):

    __name__ = None
    __parent__ = RootApp

    @classmethod
    def __getitem__(self, key):
        if key == 'new':
            return statatat.widgets.NewWidgetWidget(user=self.user)

        # I dunno about this yet.. what is this app going to do?

        raise NotImplementedError('The stuff below this needs thinking over..'
                                  )
        suffix = '.widget'
        if key.endswith(suffix):

            # Visiting /username/my_widget produces a user page detailing the
            # widget, what options it has, displaying it...  Visiting
            # /username/my_widget.widget produces the embeddable version.

            chrome = False
            key = key[:-len(suffix)]

        for conf in self.user.widget_configurations:
            if conf.name == key:
                return statatat.widgets.make_widget(conf, chrome)

        raise KeyError('No such widget %r' % key)


class APISuccess(object):

    def __init__(self, data):
        self.data = data
