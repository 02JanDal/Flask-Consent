import json
from collections import OrderedDict
from dataclasses import dataclass
from datetime import timedelta, datetime
from importlib.resources import read_text
from typing import Callable, Iterable, List, Set

from flask import current_app, render_template_string, render_template, request, jsonify, Flask
from markupsafe import Markup

from .version import version as _version
__version__ = _version


@dataclass(frozen=True)
class ConsentCategory:
    name: str
    title: str
    description: str
    default: bool
    is_required: bool


class ConsentExtensionState:
    def __init__(self, extension, app):
        self.extension = extension  # type: Consent
        self.app = app  # type: Flask

    @property
    def full_template(self):
        return self.app.config['CONSENT_FULL_TEMPLATE']

    @property
    def banner_template(self):
        return self.app.config['CONSENT_BANNER_TEMPLATE']

    @property
    def contact_mail(self):
        return self.app.config['CONSENT_CONTACT_MAIL']

    @property
    def cookie_name(self):
        return self.app.config['CONSENT_COOKIE_NAME']

    @property
    def valid_for(self):
        return timedelta(days=int(self.app.config['CONSENT_VALID_FOR_MONTHS']) / 12 * 365)

    @property
    def primary_servername(self):
        return self.app.config['CONSENT_PRIMARY_SERVERNAME']

    def html(self):
        primary_domain = self.primary_servername
        if request.endpoint == 'flask_consent' or request.consent.is_stale():
            return Markup(render_template_string(
                read_text(__name__, 'injection.html'),
                flask_consent_banner=render_template(
                    self.banner_template,
                    flask_consent_categories=self.extension.categories.values()),
                flask_consent_contact_mail=self.contact_mail,
                flask_consent_primary_domain=primary_domain,
                flask_consent_domains=self.extension.domains + [primary_domain]
            ))
        else:
            return ''


class ConsentData:
    """
    This class contains the user facing API during a request. You can access it using request.consent.
    """

    def __init__(self, state: ConsentExtensionState):
        self._state = state

        data = json.loads(request.cookies.get(self._state.cookie_name, '{}'))  # type: dict
        try:
            self._last_updated = datetime.fromisoformat(data['last_updated'])
        except (ValueError, KeyError):
            self._last_updated = datetime.utcnow()
        self._enabled = set(data['enabled']) if 'enabled' in data and isinstance(data['enabled'], list) else set()
        self._dirty = False

    def is_stale(self):
        if self._state.cookie_name not in request.cookies:
            return True

        return (self._last_updated + self._state.valid_for) < datetime.utcnow()

    def finalize(self, response):
        if self._dirty:
            response.set_cookie(self._state.cookie_name,
                                json.dumps(dict(
                                    enabled=list(self._enabled),
                                    last_updated=self._last_updated.isoformat()
                                )),
                                max_age=int(self._state.valid_for.days * 24 * 60 * 60))

    @property
    def last_updated(self) -> datetime:
        return self._last_updated

    @property
    def enabled(self) -> Set[str]:
        return self._enabled

    def __getitem__(self, key: (ConsentCategory, str)) -> bool:
        """
        Lookup if the given consent category is enabled
        :param key: The consent category, either as a ConsentCategory object or the name as a string
        :return: True if enabled, False if not
        """
        if isinstance(key, ConsentCategory):
            key = key.name
        return key in self._enabled

    def __setitem__(self, key: (ConsentCategory, str), value: bool):
        """
        Set a consent category to be enabled or disabled

        If an actual change was done we will send an updated Set-Cookie with the request.

        :param key: The consent category, either as a ConsentCategory object or the name as a string
        :param value: True if enabled, False if not
        """
        if isinstance(key, ConsentCategory):
            key = key.name
        if value and key not in self._enabled:
            self._enabled.add(key)
            self._dirty = True
            self._last_updated = datetime.utcnow()
        elif not value and key in self._enabled:
            self._enabled.remove(key)
            self._dirty = True
            self._last_updated = datetime.utcnow()


class Consent:
    """
    This Flask extension handles multi-domain cookie consent.

    When visiting a page we first check if we have a consent cookie for the current domain. If
    not we send an AJAX request to `GET primary.domain/crossdomain/consent/` which returns consent
    information for the cookies for the primary domain. If available that information is set on the
    current domain through `POST current.domain/crossdomain/consent/`. This consent information
    contains both the domains given consent for (all domains currently available) as well as what
    consent was given.

    If neither the current nor the primary domain contain consent information we ask the user. Upon
    the users selection (either in the pop up or later) we send `POST <domain>/crossdomain/consent/`
    for all domains.
    """

    def __init__(self, app: Flask = None):
        self._categories = OrderedDict()
        self._domain_loader = lambda: []

        self.app = app
        if self.app:
            self.init_app(app)

    def domain_loader(self, func: Callable[[], Iterable[str]]):
        """
        Register the method that returns the list of valid domain names
        """
        self._domain_loader = func

    @property
    def domains(self) -> List[str]:
        """
        Returns the list of valid domain names
        """
        return list(self._domain_loader())

    def init_app(self, app: Flask):
        app.config.setdefault('CONSENT_FULL_TEMPLATE', None)
        app.config.setdefault('CONSENT_BANNER_TEMPLATE', None)
        app.config.setdefault('CONSENT_CONTACT_MAIL', None)
        app.config.setdefault('CONSENT_COOKIE_NAME', '_consent')
        app.config.setdefault('CONSENT_VALID_FOR_MONTHS', 12)
        app.config.setdefault('CONSENT_PRIMARY_SERVERNAME', app.config.get('SERVER_NAME', None))
        app.config.setdefault('CONSENT_PATH', '/consent')

        if 'consent' in app.extensions:
            raise KeyError('It seems you have already registered this extension on this app')
        app.extensions['consent'] = ConsentExtensionState(self, app)

        app.add_url_rule(app.config['CONSENT_PATH'], 'flask_consent',
                         self._handle_consent_route, methods=('GET', 'POST'))

        @app.context_processor
        def context_processor():
            return dict(flask_consent_code=self.state().html)

        @app.before_request
        def prepare_request():
            request.consent = ConsentData(self.state())

        @app.after_request
        def finalize_request(response):
            request.consent.finalize(response)
            return response

    @classmethod
    def state(cls) -> ConsentExtensionState:
        return current_app.extensions['consent']

    def add_category(self, name: str, title: str, description: str,
                     default: bool, is_required: bool = False) -> ConsentCategory:
        """
        Register a new category of consent
        :param name: A name used to identify the category (e.g. preferences, analytics)
        :param title: A human readable title for the category (i.e. Preferences, Analytics)
        :param description: A human readable description on what these cookies are used for
        :param default: The default value (pre-checked or not)
        :param is_required: Whether allowing this category is required for the site to function or not
        :return:
        """
        self._categories[name] = ConsentCategory(name, title, description, default, is_required)
        return self._categories[name]

    def add_standard_categories(self):
        """
        For getting started quickly you can use this function to add 3 common categories of cookies
        """
        self.add_category(
            'required',
            'Required',
            'These cookies are required for the site to function, like handling login (remembering who '
            'you are logged in as between page visits).',
            default=True, is_required=True)
        self.add_category(
            'preferences',
            'Preferences',
            'These cookies are used for convenience functionality, like saving local preferences you have made.',
            default=True, is_required=False)
        self.add_category(
            'analytics',
            'Analytics',
            'These cookies are used to track your page visits across the site and record some basic information '
            'about your browser. We use this information in order to see how our users are using the site, '
            'allowing us to focus improvements.',
            default=True, is_required=False)

    @property
    def categories(self) -> OrderedDict:
        return self._categories

    def _handle_consent_route(self):
        if request.content_type == 'application/json':
            if request.method == 'POST':
                new = request.json
                if not isinstance(new, list):
                    return jsonify(msg='payload is not a list'), 400
                for cat in new:
                    if cat not in self._categories:
                        return jsonify(msg='invalid consent category specified: ' + cat), 400
                for cat in self._categories.keys():
                    request.consent[cat] = cat in new
            return jsonify(enabled=list(request.consent.enabled),
                           last_updated=request.consent.last_updated.isoformat())
        else:
            return render_template(
                self.state().full_template,
                consent_categories=self._categories.values(),
                consent_contact_mail=self.state().contact_mail
            )
