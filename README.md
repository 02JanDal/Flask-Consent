# Flask-Consent

[![GitHub Workflow Status](https://img.shields.io/github/workflow/status/02JanDal/Flask-Consent/Test%20and%20publish?logo=github)](https://github.com/02JanDal/Flask-Consent/actions)
[![Codacy branch grade](https://img.shields.io/codacy/grade/3d5d817d453b46eebbec3b217801fc7d/master?logo=codacy)](https://app.codacy.com/manual/02JanDal/Flask-Consent/dashboard)
[![Codacy branch coverage](https://img.shields.io/codacy/coverage/3d5d817d453b46eebbec3b217801fc7d/master?logo=codacy)](https://app.codacy.com/manual/02JanDal/Flask-Consent/dashboard)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/Flask-Consent?logo=python)](https://pypi.org/project/Flask-Consent/)
[![PyPI - Status](https://img.shields.io/pypi/status/Flask-Consent)](https://pypi.org/project/Flask-Consent/)
[![PyPI](https://img.shields.io/pypi/v/Flask-Consent)](https://pypi.org/project/Flask-Consent/)
[![License](https://img.shields.io/github/license/02JanDal/Flask-Consent)](https://github.com/02JanDal/Flask-Consent/blob/master/LICENSE)

## About

Flask-Consent is a Flask extension that helps you handle user (cookie) consent in Flask projects.

## Installation

Simply run:

```bash
pip install Flask-Consent
```

## Usage

The most basic usage:

```python
from flask import Flask
from flask_consent import Consent

app = Flask(__name__)
app.config['CONSENT_FULL_TEMPLATE'] = 'consent.html'
app.config['CONSENT_BANNER_TEMPLATE'] = 'consent_banner.html'
consent = Consent(app)
consent.add_standard_categories()
```

And add this somewhere in your Jinja2 templates: `{{ flask_consent_code() }}`

The `add_standard_categories()` adds three common categories of consent: Required, Preferences and Analytics.
If you want to use your own you can simply replace that call by calls to `add_category()`.

Use `request.consent` in order to act based on the given consent. For example:
```python
from flask import request

if request.consent['required']:
    pass
```

### Multiple domains

This package actually supports sites that are present on multiple top-level domains.
Since it's not possible to set a single cookie for them this extension instead does AJAX calls to a "primary"
domain in order to synchronize the state between the domains and prevent having to show
the user an annoying banner multiple times. To enable this simply add the following code:

```python
@consent.domain_loader
def domain_loader():
    return ['primary.tld', 'secondary.tld', 'extra.tld']
```

The primary domain used is determined using the `CONSENT_PRIMARY_SERVERNAME` configuration option,
which by default is set to `SERVER_NAME`.

### Configuration

| Option                       | Default       | Description                                                             |
|------------------------------|---------------|-------------------------------------------------------------------------|
| `CONSENT_FULL_TEMPLATE`      | None          | The template that renders the full consent page                         |
| `CONSENT_BANNER_TEMPLATE`    | None          | The template that renders the consent banner                            |
| `CONSENT_CONTACT_MAIL`       | None          | An e-mail adress that users can send questions regarding consent to     |
| `CONSENT_COOKIE_NAME`        | _consent      | The name of the cookie that stores the consent given                    |
| `CONSENT_VALID_FOR_MONTHS`   | 12            | The number of months we wait before asking for consent again            |
| `CONSENT_PRIMARY_SERVERNAME` | `SERVER_NAME` | The primary domain name, used for multi-domain deployments              |
| `CONSENT_PATH`               | `/consent`    | The path used both for accessing consent information and for AJAX calls |

### Templates

The templates gets access to the variables `flask_consent_categories` (a list fo the categories) and `flask_consent_contact_mail`
(populated from the similarly named configuration option).

Somewhere in the template you will usually be adding a set of checkboxes:

```jinja2
<input type="checkbox" id="category_{{ category.name }}"
       {% if category.default %}checked="checked"{% endif %}
       {% if category.is_required %}disabled="disabled"{% endif %}
       name="flask_consent_category" value="{{ category.name }}"/>
<label for="category_{{ category.name }}">{{ category.title }}</label>
```

**Note:** The `name="flask_consent_category"` should not be changed, as it is used internally.

(only use `category.default` in the banner template, in the full template you should replace it by `request.consent[category]`)

## Development and Testing

1.  Get the code: `git clone https://github.com/02JanDal/Flask-Consent.git`
2.  Do your changes
3.  Test the result: `tox -e py`
