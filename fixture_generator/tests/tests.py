import sys
from StringIO import StringIO

from django.core.management import call_command
from django.test import TestCase

from fixture_generator import fixture_generator
from fixture_generator.management.commands.generate_fixture import (
    linearize_requirements, CircularDependencyError)


@fixture_generator()
def test_func_1():
    pass

@fixture_generator(requires=["tests.test_func_3", "tests.test_func_4"])
def test_func_2():
    pass

@fixture_generator(requires=["tests.test_func_5"])
def test_func_3():
    pass

@fixture_generator(requires=["tests.test_func_5"])
def test_func_4():
    pass

@fixture_generator()
def test_func_5():
    pass

@fixture_generator(requires=["tests.test_func_7"])
def test_func_6():
    pass

@fixture_generator(requires=["tests.test_func_6"])
def test_func_7():
    pass

@fixture_generator('tests.Book', 'tests.Edition')
def test_books_and_editions():
    pass

@fixture_generator('tests.Author', 'tests.Book')
def test_books():
    pass

@fixture_generator('tests.Author')
def test_authors():
    pass

@fixture_generator('tests.Book', 'tests.Edition', requires=['tests.test_books', 'tests.test_authors'])
def test_editions():
    pass

class LinearizeRequirementsTests(TestCase):
    def setUp(self):
        self.available_fixtures = {}
        fixtures = [
            "test_func_1", "test_func_2", "test_func_3", "test_func_4",
            "test_func_5", "test_func_6", "test_func_7", "test_books", "test_authors"
        ]
        for fixture in fixtures:
            self.available_fixtures[("tests", fixture)] = globals()[fixture]

    def linearize_requirements(self, test_func):
        return linearize_requirements(self.available_fixtures, test_func)

    def test_basic(self):
        requirements, models = self.linearize_requirements(test_func_1)
        self.assertEqual(requirements, [test_func_1])
        self.assertEqual(models, [])

    def test_diamond(self):
        requirements, models = self.linearize_requirements(test_func_2)
        self.assertEqual(
            requirements,
            [test_func_5, test_func_3, test_func_4, test_func_2]
        )

    def test_circular(self):
        self.assertRaises(CircularDependencyError,
            linearize_requirements, self.available_fixtures, test_func_6
        )

    def test_stable_ordering(self):
        """
        Check that list of models to be serialized preserves 
        original order. 
        """
        requirements, models = self.linearize_requirements(test_books_and_editions)
        self.assertEqual(models, ["tests.Book", "tests.Edition"])

        requirements, models = self.linearize_requirements(test_editions)
        self.assertEqual(models, ["tests.Author", "tests.Book", "tests.Edition"])


class ManagementCommandTests(TestCase):
    def generate_fixture(self, fixture, **options):
        out = sys.stdout
        sys.stdout = StringIO()
        try:
            call_command("generate_fixture", fixture, **options)
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = out
        return output

    def test_basic(self):
        output = self.generate_fixture("tests.test_1")
        self.assertEqual(output, """[{"pk": 1, "model": "tests.author", "fields": {"name": "Tom Clancy"}}, {"pk": 2, "model": "tests.author", "fields": {"name": "Daniel Pinkwater"}}]""")

    def test_auth(self):
        # All that we're checking for is that it doesn't hang on this call,
        # which would happen if the auth post syncdb hook goes and prompts the
        # user to create an account.
        output = self.generate_fixture("tests.test_2")
        self.assertEqual(output, "[]")

    def test_natural_keys(self):
        output = self.generate_fixture("tests.test_3", use_natural_keys=True)
        self.assertEqual(output, """[{"pk": 1, "model": "tests.book", "fields": {"author": ["Issac Asimov"], "title": "Foundation"}}]""")
