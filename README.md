JudgeD: Probabilistic Datalog
=============================

JudgeD is a proof-of-concept implementation of a probabilistic variant of
[Datalog](https://en.wikipedia.org/wiki/Datalog). JudgeD is available under the
MIT license.

JudgeD requires [Python 3.4](https://www.python.org/) or newer.


Quick Start
-----------

  1. `pip install https://github.com/utdb/judged/releases/download/v0.9.dev0/judged-0.9.dev0.tar.gz` the downloaded file
  2. Have a look at the examples in `examples/` in this repository, or play
     with the interactive interpreter: `judged`


Development Start
-----------------

  1. `git clone` this repository
  2. Set up a virtualenv with python3.4+
  3. Get to work on the source, using `./judged.py` as entry point
  4. Run tests with `python -m tests`
  5. Package source release with `python setup.py sdist`


Variants
--------

The JudgeD solver currently has three variants: `deterministic`, `exact` and
`montecarlo`.

The `deterministic` variant is the deterministic basis of JudgeD. It is an SLDNF
based implementation of Datalog with negation in Python.

The `exact` and `montecarlo` variants are two proof-of-concept implementations
of probabilistic datalog. The `exact` version determines the exact sentence
describing the validity of the answers, it does net calculate probabilities, nor
does it handle negation. The `montecarlo` version calculate answer probabilities
through Monte Carlo simulation, it approximates the probabilities but does not
provide an exact sentence.


Syntax
------

The syntax of JudgeD program closely resembles traditional datalog, with the
addition of the descriptive sentences. Additionally, the probabilities attached
to the labels are included in the syntax. An example of a simple coin-flip
would be:

    heads(c1) [x=1].
    tails(c1) [x=2].

    @P(x=1) = 0.5.
    @P(x=2) = 0.5.

The first two lines establish simple facts and attach sentences to make them
mutually exclusive. The third line contain annotations that attach
probabilities to the labels to allow the calculation of answer probabilities.
When presented with the query `heads(C)?` the answer `heads(c1)` has a
probability of 0.5.

The descriptive sentences are propositional logic expressions that use labels
of the form `partition=value` as atoms. It is allowed to use non-numeric
values, i.e., labels like `x=heads` or `choice=opens_door_1` are valid. Complex
dependencies between clauses can be given through the combination of these
labels with the `and`, `or` and `not` operations leading to sentences like
`(x=1 and y=2) or z=1`.

For the Monte Carlo simulation, the probabilities for each label have to be
defined. This can be done manually per label:

    @P(x=1) = 0.333.
    @P(x=2) = 0.333.
    @P(x=3) = 0.333.

Or, if a uniform distribution is desired, with:

    @uniform(x).

Note that the `@uniform` annotation should be placed after all values for the
given partition have been defined.


Interpreter
-----------

Interpreter parameter documentation can be produced by invoking `datalog.py`
with the `--help` flag. The subcommands each have their own help documentation.
For ease of use, some useful combinations are given here.

`datalog.py exact --help`: Gets the full list of options for the `exact` variant
of JudgeD.

`datalog.py deterministic -V`: runs an interactive deterministic datalog prompt
in verbose mode, showing each statement is it is processed.

`datalog.py deterministic -f color -v -i examples/power.dl`: `-f color`
Explicitly declares colored output formatting, `-v` runs in verbose mode to show
each statement as it is processed, and `-i` switches to interactive mode after
the given files are processed.

`datalog.py deterministic -d examples/ancestor.dl`: Runs the ancestor.dl example
file with a debugging trace of the query answering process.
