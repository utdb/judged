"""
Execution context for a JudgeD program.
"""

import random
import collections
import contextlib

from judged.logic import Knowledge, Prover,  ExactProver


Answer = collections.namedtuple('Answer', ['clause', 'probability'])

class Result:
    def __init__(self, answers, **notes):
        self.answers = answers
        self.notes = notes


class Context:
    def __init__(self, knowledge, prover):
        self.knowledge = knowledge
        self.prover = prover
        self.extensions = {}
        self.prob = {}

    def add_probability(self, partitioning, part, prob):
        """Stores the probability attached to a partition."""
        self.prob.setdefault(partitioning, dict())
        self.prob[partitioning][part] = prob

    def check(self, key, part):
        raise NotImplementedError()

    @contextlib.contextmanager
    def _ask_extension(self, ext):
        # fire the extension's before_asks
        ext._do_before_ask(self)
        # yield to the body of the with block
        yield
        # fire the extension's after_asks
        ext._do_after_ask(self)

    def ask(self, query):
        # Make an ExitStack to dynamically add extension ask contexts for each
        # extension we have
        with contextlib.ExitStack() as ext_stack:
            for ext in self.extensions.values():
                # create and register extension ask context helper
                ext_stack.enter_context(self._ask_extension(ext))
            # with all extension ask contexts ready, fire the real ask
            return self._ask(query)

    def _ask(self, query):
        answers = self.prover.ask(query, self.check)
        return Result([Answer(a, None) for a in answers])

    def use_extension(self, extension, config):
        # fire the extensions do_setups
        extension._do_setup(self, config)
        # if none of the above failed, we add the extension
        self.extensions[extension.name] = extension


class DeterministicContext(Context):
    def __init__(self, debugger=None):
        knowledge = Knowledge(self)
        super().__init__(knowledge, Prover(knowledge, debugger=debugger))
        self.choices = {}

    def check(self, key, part):
        try:
            self.choices[key] == part
        except KeyError:
            raise JudgedError("Can not check whether label '{key}={part}' holds, no part is selected for the partitioning '{key}'.".format(
                key=key,
                part=part
            ))

    def select_world_set(self, key, part):
        self.choices[key] = part

    def reset_world_set(self):
        self.choices.clear()


class ExactContext(Context):
    def __init__(self, debugger=None):
        knowledge = Knowledge(self)
        super().__init__(knowledge, ExactProver(knowledge, debugger=debugger))

    def check(self, key, part):
        # NOTE: This can be used to allow "conditioned queries" by restricting the world set
        return True


class MontecarloContext(Context):
    def __init__(self, number=1000, approximate=0, debugger=None):
        knowledge = Knowledge(self)
        super().__init__(knowledge, Prover(knowledge, debugger=debugger))
        self.choices = {}
        self.number = number
        self.approximate = approximate

    def check(self, key, part):
        if key not in self.choices:
            self.choices[key] = self.pick(key)
        return self.choices[key] == part

    def pick(self, partitioning):
        """
        Randomly picks a partition based on the known partitions. The selection
        is weighted by the assigned probabilities.
        """
        r = random.random()
        a = 0.0
        try:
            for part, prob in self.prob[partitioning].items():
                a += prob
                if a >= r:
                    return part
            raise JudgedError("Probabilities for partitioning '{}' do not sum to 1.0.".format(partitioning))
        except:
            raise JudgedError("Probabilities for partitioning '{}' not set".format(partitioning))

    def _ask(self, query):
        for ext in self.extensions:
            ext._do_before_ask(self)

        count = 0
        worlds = collections.Counter()
        answers = collections.Counter()

        def p(c):
            return c / count

        def exact(w):
            result = 1
            for p,v in w:
                result *= self.prob[p][v]
            return result

        def error():
            result = 0
            for w in worlds:
                result += (exact(w) - p(worlds[w]))**2
            result /= len(worlds)
            return result**0.5

        while self.number == 0 or count < self.number:
            count += 1

            self.choices.clear()
            answer = list(self.prover.ask(query, self.check))
            world = frozenset(self.choices.items())

            for a in answer:
                answers[a] += 1
            worlds[world] += 1

            if self.approximate is not None:
                if error() <= self.approximate:
                    break

        result = Result([Answer(a, p(c)) for a, c in answers.items()], iterations=count, error=error())

        for ext in self.extensions:
            ext._do_after_ask(self)

        return result
