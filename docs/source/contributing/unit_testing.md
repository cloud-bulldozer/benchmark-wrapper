# Testing

benchmark-wrapper uses [tox](https://pypi.org/project/tox/) and [pytest](https://docs.pytest.org/en/6.2.x/) for unit testing as well as documentation build testing.

As a quick reminder, unit testing is defined as follows by [STF](https://softwaretestingfundamentals.com/unit-testing/):

> UNIT TESTING, also known as COMPONENT TESTING,  is a level of software testing where individual units / components of a software are tested. The purpose is to validate that each unit of the software performs as designed.

The goal for unit testing within benchmark-wrapper specifically is to ensure that all shared units (common modules and functionality) behave as expected, in order to create a solid foundation that all benchmarks may be based upon.

For documentation build testing, the goal is to ensure that the documentation can build without errors and that there are no broken external links.

Here are the main takeaways:

* To write unit tests for a module, place them in ``tests/unit/test_<module>.py``.
* Use Tox to invoke pytest unit tests and documentation build tests, by choosing from the following environments: ``py{36,37,38,39}-{unit,docs}``.
* Use coverage reports to ensure thorough code testing.

## Tox Usage

There are eight distinct environments that Tox is configured for (through the ``tox.ini`` file within the project root), which is a permutation across four versions of Python and our two testing goals. These environments can be invoked by picking values from the following sets:

``tox -e py{36,37,38,39}-{unit,docs}``

For instance, using ``py36-unit`` will run unit tests for Python 3.6, while ``py38-docs`` will run a documentation build test for Python 3.8.


## Writing Unit Tests

Unit tests are placed under the ``tests/unit`` directory, container within individual Python modules. To keep a consistent structure, each module under this directory should correspond to one module within benchmark-wrapper. As an example, to create unit tests for ``snafu.module``, place them within ``tests/unit/test_module.py``.

For more information on how pytest can be leveraged to write unit tests, please check read the [pytest documentation](https://docs.pytest.org/en/6.2.x/example/index.html).

## Code Coverage

When unit tests are invoked using tox, [pytest-cov](https://pytest-cov.readthedocs.io/en/latest/readme.html) will be used to generate a coverage report, showing which lines were covered. Additionally, a [coverage file](https://coverage.readthedocs.io/en/coverage-5.5/) will be placed in the project root with the tox environment used as the file extension (i.e. ``.coverage.py{36,37,38,39}-unit``). Please use these coverage resources to help write unit tests for your PRs as needed. Note that code for benchmark wrappers are not included in these coverage reports, as benchmarks will be tested with [functional tests](https://softwaretestingfundamentals.com/functional-testing/), rather than unit tests.
