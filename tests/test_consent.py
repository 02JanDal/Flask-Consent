# -*- coding: utf-8 -*-
#
# This file is part of Flask-Consent
# Copyright (C) 2020 Jan Dalheimer

import unittest

from flask import Flask, jsonify, request, render_template_string
from flask.testing import FlaskClient
from flask_testing import TestCase

from flask_consent import Consent, ConsentData


def make_app_and_consent():
    app = Flask(__name__)
    app.config['CONSENT_FULL_TEMPLATE'] = 'full.html'
    app.config['CONSENT_BANNER_TEMPLATE'] = 'banner.html'
    app.config['CONSENT_CONTACT_MAIL'] = 'test@test.test'
    app.config['CONSENT_PRIMARY_SERVERNAME'] = 'primary.test'
    consent = Consent(app)
    consent.add_standard_categories()

    @app.route('/')
    def test():
        return jsonify(required=request.consent['required'],
                       preferences=request.consent['preferences'],
                       analytics=request.consent['analytics'])

    @app.route('/banner')
    def banner():
        return render_template_string('''
                <html>
                <head>{{ flask_consent_code() }}</head>
                <body></body>
                </html>
                ''')

    return app, consent


class WebTest(TestCase):
    client: FlaskClient

    def create_app(self):
        app, _ = make_app_and_consent()
        return app

    def test_first_visit_uses_default(self):
        resp = self.client.get('/')
        self.assert200(resp)
        self.assertDictEqual(resp.json, dict(
            required=True,
            preferences=True,
            analytics=True
        ))

    def test_first_visit_includes_banner(self):
        resp = self.client.get('/banner')
        self.assert200(resp)
        self.assertIn('id="flask_consent_banner"', resp.data.decode(resp.charset))

    def test_no_banner_after_accept(self):
        resp = self.client.post('/consent', json=['required', 'preferences'])
        self.assert200(resp)
        resp = self.client.get('/banner')
        self.assert200(resp)
        self.assertNotIn('id="flask_consent_banner"', resp.data.decode(resp.charset))

    def test_accept_consent(self):
        self.client.get('/')
        resp = self.client.post('/consent', json=['required', 'preferences'])
        self.assert200(resp)
        self.assertSetEqual(set(resp.json['enabled']), {'required', 'preferences'})
        resp = self.client.get('/')
        self.assert200(resp)
        self.assertDictEqual(resp.json, dict(
            required=True,
            preferences=True,
            analytics=False
        ))

    def test_change_consent(self):
        resp = self.client.post('/consent', json=['required', 'preferences'])
        self.assert200(resp)
        self.assertSetEqual(set(resp.json['enabled']), {'required', 'preferences'})
        resp = self.client.post('/consent', json=['required', 'analytics'])
        self.assert200(resp)
        self.assertSetEqual(set(resp.json['enabled']), {'required', 'analytics'})
        resp = self.client.get('/')
        self.assert200(resp)
        self.assertDictEqual(resp.json, dict(
            required=True,
            preferences=False,
            analytics=True
        ))

    def test_render_banner(self):
        resp = self.client.get('/banner')
        self.assert200(resp)

    def test_render_full(self):
        resp = self.client.get('/consent')
        self.assert200(resp)
        self.assertNotIn('id="flask_consent_banner"', resp.data.decode(resp.charset))

    def test_post_invalid_type(self):
        resp = self.client.post('/consent', json=dict(foo='bar'))
        self.assert400(resp)
        self.assertDictEqual(resp.json, dict(msg='payload is not a list'))

    def test_post_unknown_category(self):
        resp = self.client.post('/consent', json=['foo'])
        self.assert400(resp)
        self.assertDictEqual(resp.json, dict(msg='invalid consent category specified: foo'))


class MultiDomainTest(TestCase):
    def create_app(self):
        app, consent = make_app_and_consent()

        @consent.domain_loader
        def domain_loader():
            return ['secondary.test', 'another.test']

        return app

    def test_injection_includes_domains(self):
        resp = self.client.get('/consent')
        self.assert200(resp)
        self.assertIn('primary.test', resp.data.decode(resp.charset))
        self.assertIn('secondary.test', resp.data.decode(resp.charset))
        self.assertIn('another.test', resp.data.decode(resp.charset))


class BasicTest(unittest.TestCase):
    def test_double_register(self):
        app = Flask(__name__)
        Consent(app)
        self.assertRaises(KeyError, lambda: Consent(app))

    def test_get_categories(self):
        consent = Consent()
        consent.add_standard_categories()
        self.assertEqual(len(consent.categories), 3)
        self.assertEqual(consent.categories['required'].title, 'Required')

    def test_get_set_categories(self):
        app = Flask(__name__)
        consent = Consent(app)
        consent.add_standard_categories()

        with app.test_request_context():
            data = ConsentData(consent.state())
            self.assertIs(data['analytics'], True)
            data['analytics'] = False
            self.assertIs(data['analytics'], False)

            preferences_category = consent.categories['preferences']
            self.assertIs(data[preferences_category], True)
            data[preferences_category] = False
            self.assertIs(data[preferences_category], False)
