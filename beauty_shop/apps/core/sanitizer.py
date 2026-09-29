"""Allow-list based HTML sanitizer for content written in the admin editor."""
import nh3

ALLOWED_TAGS = {
    "p", "br", "div", "span", "h2", "h3", "h4",
    "strong", "b", "em", "i", "u", "s", "mark", "small",
    "ul", "ol", "li", "blockquote", "hr",
    "a", "img", "figure", "figcaption",
    "table", "thead", "tbody", "tr", "th", "td",
}

ALLOWED_ATTRIBUTES = {
    "a": {"href", "title", "target"},
    "img": {"src", "alt", "width", "height", "loading"},
    "th": {"colspan", "rowspan"},
    "td": {"colspan", "rowspan"},
}

URL_SCHEMES = {"http", "https", "mailto", "tel"}


def sanitize_html(value):
    if not value:
        return ""
    return nh3.clean(
        value,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes=URL_SCHEMES,
        link_rel="noopener noreferrer",
        strip_comments=True,
    )
