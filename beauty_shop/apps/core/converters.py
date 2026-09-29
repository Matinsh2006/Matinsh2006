class UnicodeSlugConverter:
    """Like Django's ``slug`` converter but also accepts Persian letters."""

    regex = r"[-\w]+"

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value
