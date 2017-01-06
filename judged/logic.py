"""
Core judged module that provides classes for terms, predicates, literals, and
clauses as well as a Knowledge base implementation and a Prover.
"""

import random
import collections

from judged import *
from judged import worlds
import judged.primitives


Answer = collections.namedtuple('Answer', ['clause', 'probability'])

class Result:
    def __init__(self, answers, **notes):
        self.answers = answers
        self.notes = notes


class Context:
    def __init__(self, knowledge, prover):
        self.knowledge = knowledge
        self.prover = prover
        self.prob = {}

    def add_probability(self, partitioning, part, prob):
        """Stores the probability attached to a partition."""
        self.prob.setdefault(partitioning, dict())
        self.prob[partitioning][part] = prob

    def check(self, key, part):
        raise NotImplementedError()

    def ask(self, query):
        answers = self.prover.ask(query, self.check)
        return Result([Answer(a, None) for a in answers])


class DeterministicContext(Context):
    def __init__(self, debugger=None):
        knowledge = Knowledge()
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
        knowledge = Knowledge()
        super().__init__(knowledge, ExactProver(knowledge, debugger=debugger))

    def check(self, key, part):
        # NOTE: This can be used to allow "conditioned queries" by restricting the world set
        return True


class MontecarloContext(Context):
    def __init__(self, number=1000, approximate=0, debugger=None):
        knowledge = Knowledge()
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

    def ask(self, query):
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

        return Result([Answer(a, p(c)) for a, c in answers.items()], iterations=count, error=error())


class Knowledge:
    """
    The knowledge base over which queries can be posed through a Prover.

    The knowledge base keeps track of the asserted clauses and the primitive
    predicates. It starts out with only the built-in equals predicate.
    """
    def __init__(self):
        self.db = dict()
        self.prim = dict()

        judged.primitives.register_primitives(self)

    def is_safe(self, clause):
        """
        Checks if the clause is safe. A clause is safe if the following
        conditions are met: all variables in the head are also present in the
        body, all variables in negated literals are also present in positive
        literals in the body.
        """
        # head and body variables
        head_vars = {v for v in clause.head if not v.is_const()}
        body_vars = {v for lit in clause for v in lit if not v.is_const()}
        first = head_vars <= body_vars

        # positive and negative variables
        pos_vars = {v for lit in clause for v in lit if not v.is_const() and lit.polarity == True}
        neg_vars = {v for lit in clause for v in lit if not v.is_const() and lit.polarity == False}
        second = neg_vars <= pos_vars

        return first and second

    def assert_clause(self, clause):
        """Asserts a clause. Raises an error if the clause is unsafe."""
        if not self.is_safe(clause):
            raise JudgedError("Asserted clause is unsafe: '{}'".format(clause))

        pred = clause.head.pred
        db = self.db.setdefault(pred, dict())
        db[clause.id] = clause
        return clause

    def retract_clause(self, clause):
        """Retracts a clause."""
        pred = clause.head.pred
        db = self.db.get(pred, None)
        if db:
            db.pop(clause.id, None)
        if not db:
            self.db.pop(pred, None)
        return clause

    def add_primitive(self, predicate, gen):
        """Creates a primitive predicate by coupling it to a generator."""
        self.prim[predicate] = gen

    def clauses(self, literal, prover):
        """
        A generator of all clauses that have the predicate as head. Clauses are
        produced regardless of the whether the predicate is a primitive or not.

        The prover is given to provide the state information to native
        predicates.
        """
        pred = literal.pred

        # produce primitive clauses
        if pred in self.prim:
            yield from self.prim[pred](literal, prover)

        # produce asserted clauses
        if pred in self.db:
            yield from self.db[pred].values()

    def parts(self, partitioning):
        # NOTE: Used exclusively for worlds.exclusion_matrix and uniform distribution
        result = set()
        for db in self.db.values():
            for clause in db.values():
                result.update(lbl[1] for lbl in clause.sentence.labels() if lbl[0]==partitioning)
        return result


class Subgoal:
    def __init__(self, literal):
        self.literal = literal
        self.anss = set()
        self.poss = list()
        self.negs = list()
        self.comp = False

    def __repr__(self):
        return "Subgoal(literal={}, anss={}, poss={}, negs={}, comp={})".format(self.literal, self.anss, self.poss, self.negs, self.comp)


class Waiter:
    def __init__(self, literal, clause, selected):
        self.literal = literal
        self.clause = clause
        self.selected = selected

    def __repr__(self):
        return "Waiter(literal={}, clause={}, selected={})".format(self.literal, self.clause, self.selected)


class Frame:
    def __init__(self, subgoal, dfn, poslink, neglink):
        self.subgoal = subgoal
        self.dfn = dfn
        self.poslink = poslink
        self.neglink = neglink


class Mins:
    def __init__(self, posmin, negmin):
        self.posmin = posmin
        self.negmin = negmin

    def __str__(self):
        return "(posmin={}, negmin={})".format(self.posmin, self.negmin)


class Prover:
    """
    The prover can prove queries over a knowledge base. Use the ask method with
    a literal to get a list of facts matching the query.

    The knowledge base need only support a clauses method which, given a
    literal and a prover instances, returns a list or generator that produces
    clauses that have the given predicate in theirhead.

    A prover is not thread-safe. Multi-threaded use requires the construction
    of multiple provers.
    """
    def __init__(self, knowledge, debugger=None):
        self.kb = knowledge
        self.debugger = debugger
        # initialize bookkeeping
        self.subgoals = dict()
        self.stack = list()
        self.count = 1
        self.checker = None

    def ask(self, query, checker):
        """
        Sets up and activates the subgoal search machinery. The answer is then
        returned as a list of proven facts. [Chen et al., Figure 13, p. 181]
        """
        self.count = 1
        self.subgoals.clear()
        self.stack.clear()
        self.checker = checker

        subgoal = Subgoal(query)
        self.subgoals[query.tag()] = subgoal

        dfn = self.count
        self.stack.append(Frame(subgoal, dfn, dfn, float('inf')))
        self.count += 1

        if self.debugger: self.debugger.ask(query)
        self.slg_subgoal(query, Mins(dfn, float('inf')))
        if self.debugger: self.debugger.done(subgoal)

        seen = set()
        for answer in subgoal.anss:
            if answer.head not in seen:
                seen.add(answer.head)
                yield Clause(answer.head, [], [])

    def allows(self, sentence):
        """
        Checks if the sentence is allowed in the set of worlds currently
        chosen. This method updates self.choices if a choice is needed.
        """
        return worlds.evaluate(sentence, self.checker)

    def slg_resolve(self, clause, selected, other):
        """
        Determines the SLG resolvent of a clause G with selected literal Li and
        some other clause C. [Chen et al., Definition 2.4, p. 171]
        """
        if not clause.body:
            return None
        renamed = other.rename()
        env = selected.unify(renamed.head)
        if env is None:
            return None

        body = []
        for lit in clause.body:
            if lit == selected:
                body.extend(renamed.body)
            else:
                body.append(lit)
        return Clause(clause.head, body, clause.delayed).subst(env)

    def slg_factor(self, clause, selected, other):
        """
        Deteremines the SLG factor of a clause G with selected literal Li and
        an answer clause C. [Chen et al., Definition 2.5, p. 171]
        """
        if not other.delayed:
            return None
        renamed = other.rename()
        env = selected.unify(renamed.head)
        if env is None:
            return None

        body = [lit for lit in clause.body if lit != selected]
        delayed = clause.delayed + [selected]
        return Clause(clause.head, body, delayed).subst(env)

    def slg_subgoal(self, literal, mins):
        """
        [Chen et al., Figure 14, p. 182]
        """
        if self.debugger: self.debugger.subgoal(literal)
        for clause in self.kb.clauses(literal, self):
            if not self.allows(clause.sentence):
                continue
            resolvent = self.slg_resolve(Clause(literal, [literal]), literal, clause)
            if resolvent is not None:
                self.slg_newclause(literal, resolvent, mins)
        self.slg_complete(literal, mins)

    def select(self, clause):
        """
        Selects a literal from the clause for expansion. Gets a non-negative
        literal first. If that is not possible, try for a grounded negative
        literal. If that is not possible, select the first literal.
        """
        if not clause.body:
            return None

        for lit in clause.body:
            if lit.polarity == True:
                return lit

        for lit in clause.body:
            if lit.polarity == False and lit.is_grounded():
                return lit

        return clause.body[0]

    def slg_newclause(self, literal, clause, mins):
        """
        [Chen et al., Figure 14, p. 182]
        """
        selected = self.select(clause)
        if selected is None:
            if self.debugger: self.debugger.answer(literal, clause, selected)
            self.slg_answer(literal, clause, mins)
        elif selected.polarity == True:
            if self.debugger: self.debugger.clause(literal, clause, selected, True)
            self.slg_positive(literal, clause, selected, mins)
        elif selected.polarity == False and selected.is_grounded():
            if self.debugger: self.debugger.clause(literal, clause, selected, False)
            self.slg_negative(literal, clause, selected.invert(), mins)
        else:
            raise JudgedError('Selected a non-grounded negative literal.')

    def answer_subsumed_by(self, clause, answers):
        # Due to the safety constraints the clause's head will feature no
        # variables if the body is empty. slg_answer, and thus
        # answer_subsumed_by, is only called after no literal can be selected
        # so the body must be empty. Judged does not support compound terms,
        # so call subsumption is not possible.
        #
        # However, subsumption through equality is still possible. So, we check
        # all answers to see if the same head was already found (ignoring the
        # sentence of the clause).
        for cl in answers:
            if cl.head == clause.head:
                return True
        return False

    def other_answer_with_same_head(self, clause, answers):
        for a in answers:
            if clause == a: continue
            if clause.head == a.head:
                return True
        return False

    def slg_answer(self, literal, clause, mins):
        """
        [Chen et al., Figure 15, p. 183]
        """
        subgoal = self.subgoals[literal.tag()]
        if self.answer_subsumed_by(clause, subgoal.anss):
            return
        subgoal.anss.add(clause)
        if not clause.delayed:
            subgoal.negs.clear()
            for waiter in subgoal.poss:
                resolvent = self.slg_resolve(waiter.clause, waiter.selected, clause)
                if resolvent is not None:
                    self.slg_newclause(waiter.literal, resolvent, mins)
        else:
            if self.other_answer_with_same_head(clause, subgoal.anss):
                return
            for waiter in subgoal.poss:
                factor = self.slg_factor(waiter.clause, waiter.selected, clause)
                if factor is not None:
                    self.slg_newclause(waiter.literal, factor, mins)

    def slg_positive(self, literal, clause, selected, mins):
        """
        [Chen et al., Figure 16, p. 183]
        """
        if selected.tag() not in self.subgoals:
            subgoal = Subgoal(selected)
            subgoal.poss.append(Waiter(literal, clause, selected))
            self.subgoals[selected.tag()] = subgoal
            dfn = self.count
            poslink = self.count
            neglink = float('inf')
            self.stack.append(Frame(subgoal, dfn, poslink, neglink))
            self.count += 1
            bmins = Mins(dfn, float('inf'))
            self.slg_subgoal(selected, bmins)
            self.update_solution(literal, selected, True, mins, bmins)
        else:
            subgoal = self.subgoals[selected.tag()]
            if not subgoal.comp:
                subgoal.poss.append(Waiter(literal, clause, selected))
                self.update_lookup(literal, selected, True, mins)
            todo = []
            def fact_in_collection(fact, collection):
                for cl in collection:
                    if cl.head == fact:
                        return True
                return False
            for c in subgoal.anss:
                if fact_in_collection(c.head, subgoal.anss):
                    todo.append(self.slg_resolve(clause, selected, Clause(c.head,[],[])))
                else:
                    todo.append(self.slg_factor(clause, selected, c))
            for c in todo:
                self.slg_newclause(literal, c, mins)

    def clause_remove_lit(self, clause, lit):
        """
        Let result be the clause with the literal removed.
        """
        body = list(clause.body)
        delayed = list(clause.delayed)
        try: body.remove(lit)
        except ValueError: pass
        try: delayed.remove(lit)
        except ValueError: pass
        return Clause(clause.head, body, delayed)

    def clause_delay_lit(self, clause, lit):
        """
        Let result be the clause with the literal delayed.
        """
        body = list(clause.body)
        body.remove(lit)
        delayed = list(clause.delayed)
        delayed.append(lit)
        return Clause(clause.head, body, delayed)

    def slg_negative(self, literal, clause, selected, mins):
        """
        [Chen et al., Figure 17, p. 184]
        """
        if selected.tag() not in self.subgoals:
            subgoal = Subgoal(selected)
            subgoal.negs.append(Waiter(literal, clause, selected))
            self.subgoals[selected.tag()] = subgoal
            dfn = self.count
            poslink = dfn
            neglink = float('inf')
            self.stack.append(Frame(subgoal, dfn, poslink, neglink))
            self.count += 1
            bmins = Mins(dfn, float('inf'))
            self.slg_subgoal(selected, mins)
            self.update_solution(literal, selected, False, mins, bmins)
        else:
            subgoal = self.subgoals[selected.tag()]
            if not subgoal.comp:
                if Clause(selected, [], []) not in subgoal.anss:
                    subgoal.negs.append(Waiter(literal, clause, selected))
                    self.update_lookup(literal, selected, False, mins)
            else:
                negselected = selected.invert()
                if not subgoal.anss:
                    self.slg_newclause(literal, self.clause_remove_lit(clause, negselected), mins)
                elif Clause(selected, [], []) not in subgoal.anss:
                    self.slg_newclause(literal, self.clause_delay_lit(clause, negselected), mins)

    def update_lookup(self, literal, selected, sign, mins):
        """
        [Chen et al., Figure 18, P. 186]
        """
        sga = self.subgoals[literal.tag()]
        fa = None
        for f in self.stack: # stack frame lookup ~_~
            if f.subgoal is sga:
                fa = f
                break
        assert fa is not None
        sgb = self.subgoals[selected.tag()]
        fb = None
        for f in self.stack: # stack frame lookup ~_~
            if f.subgoal is sgb:
                fb = f
                break
        assert fb is not None

        if sign:
            fa.poslink = min(fa.poslink, fb.poslink)
            fa.neglink = min(fa.neglink, fb.neglink)
            mins.posmin = min(mins.posmin, fa.poslink)
            mins.negmin = min(mins.negmin, fb.neglink)
        else:
            fa.neglink = min(fa.neglink, fb.poslink, fb.neglink)
            mins.negmin = min(mins.negmin, fb.poslink, fb.neglink)

    def update_solution(self, literal, selected, sign, mins, bmins):
        """
        [Chen et al., Figure 18, p. 186]
        """
        sga = self.subgoals[literal.tag()]
        fa = None
        for f in self.stack: # stack frame lookup ~_~
            if f.subgoal is sga:
                fa = f
                break
        assert fa is not None
        sgb = self.subgoals[selected.tag()]

        if not sgb.comp:
            self.update_lookup(literal, selected, sign, mins)
        else:
            fa.poslink = min(fa.poslink, bmins.posmin)
            fa.neglink = min(fa.neglink, bmins.negmin)
            mins.posmin = min(mins.posmin, bmins.posmin)
            mins.negmin = min(mins.negmin, bmins.negmin)

    def slg_complete(self, literal, mins):
        sga = self.subgoals[literal.tag()]
        fa = None
        for f in self.stack: # stack frame lookup ~_~
            if f.subgoal is sga:
                fa = f
                break
        assert fa is not None

        fa.poslink = min(fa.poslink, mins.posmin)
        fa.neglink = min(fa.neglink, mins.negmin)

        if fa.poslink == fa.dfn and fa.neglink == float('inf'):
            popped = []
            while True:
                last = self.stack.pop()
                popped.append(last)
                if last is fa:
                    break
            todo = []
            for fb in popped:
                negs = fb.subgoal.negs
                fb.subgoal.comp = True
                fb.subgoal.poss.clear()
                fb.subgoal.negs.clear()
                if self.debugger: self.debugger.complete(fb.subgoal)
                negselected = fb.subgoal.literal.invert()
                for waiter in negs:
                    if not fb.subgoal.anss:
                        todo.append((waiter.literal, self.clause_remove_lit(waiter.clause, negselected)))
                    elif Clause(selected, [], []) not in subgoal.anss:
                        todo.append((waiter.literal, self.clause_delay_lit(waiter.clause, negselected)))
                mins.posmin = float('inf')
                mins.negmin = float('inf')
                for literal, clause in todo:
                    self.slg_newclause(literal, clause, mins)
        elif fa.poslink == fa.dfn and fa.neglink >= fa.dfn:
            frames = self.stack[self.stack.index(fa):]
            frames.reverse()
            todo = []
            for fb in frames:
                negselected = fb.subgoal.literal.invert()
                for waiter in fb.subgoal.negs:
                    todo.append((waiter.literal, self.clause_delay_lit(waiter.clause, negselected)))
                fb.neglink = float('inf')
                fb.subgoal.negs.clear()
            mins.posmin = self.stack[-1:][0].dfn
            mins.negmin = float('inf')
            for literal, clause in todo:
                self.slg_newclause(literal, clause, mins)
            for fb in frames:
                self.slg_complete(fb.subgoal.literal, mins)


class ExactProver(Prover):
    """Prover for symbolic sentence handling. Subclasses the normal prover and
    only replaces those methods that are modified with respect to the normal
    operations."""
    def ask(self, query, checker):
        """
        Sets up and activates the subgoal search machinery. The answer is then
        returned as a list of proven facts. [Chen et al., Figure 13, p. 181]
        """
        self.count = 1
        self.subgoals.clear()
        self.stack.clear()
        self.checker = checker

        subgoal = Subgoal(query)
        self.subgoals[query.tag()] = subgoal

        dfn = self.count
        self.stack.append(Frame(subgoal, dfn, dfn, float('inf')))
        self.count += 1

        if self.debugger: self.debugger.ask(query)
        self.slg_subgoal(query, Mins(dfn, float('inf')))
        if self.debugger: self.debugger.done(subgoal)

        seen = dict()
        for answer in subgoal.anss:
            seen.setdefault(answer.head, [])
            seen[answer.head].append(answer.sentence)
        for head, sentences in seen.items():
            yield Clause(head, [], [], worlds.disjunct(*sentences))

    def slg_resolve(self, clause, selected, other):
        """
        Determines the SLG resolvent of a clause G with selected literal Li and
        some other clause C. [Chen et al., Definition 2.4, p. 171]
        """
        if not clause.body:
            return None
        renamed = other.rename()
        env = selected.unify(renamed.head)
        if env is None:
            return None

        body = []
        for lit in clause.body:
            if lit == selected:
                body.extend(renamed.body)
            else:
                body.append(lit)

        sentence = worlds.conjunct(clause.sentence, other.sentence)
        if worlds.falsehood(sentence, self.kb):
            return None

        return Clause(clause.head, body, clause.delayed, sentence).subst(env)

    def slg_factor(self, clause, selected, other):
        """
        Deteremines the SLG factor of a clause G with selected literal Li and
        an answer clause C. [Chen et al., Definition 2.5, p. 171]
        """
        if not other.delayed:
            return None
        renamed = other.rename()
        env = selected.unify(renamed.head)
        if env is None:
            return None

        body = [lit for lit in clause.body if lit != selected]
        delayed = clause.delayed + [selected]
        return Clause(clause.head, body, delayed, worlds.conjunct(clause.sentence, other.sentence)).subst(env)

    def slg_newclause(self, literal, clause, mins):
        """
        [Chen et al., Figure 14, p. 182]
        """
        selected = self.select(clause)
        if selected is None:
            if self.debugger: self.debugger.answer(literal, clause, selected)
            self.slg_answer(literal, clause, mins)
        elif selected.polarity == True:
            if self.debugger: self.debugger.clause(literal, clause, selected, True)
            self.slg_positive(literal, clause, selected, mins)
        elif selected.polarity == False and selected.is_grounded():
            if self.debugger: self.debugger.clause(literal, clause, selected, False)
            raise JudgedError('Discovered a negative literal during reasoning: exact prover can not handle negation.')
        else:
            raise JudgedError('Selected a non-grounded negative literal.')

    def answer_subsumed_by(self, clause, answers):
        # Due to the safety constraints the clause's head will feature no
        # variables if the body is empty. slg_answer, and thus
        # answer_subsumed_by, is only called after no literal can be selected
        # so the body must be empty. Judged does not support compound terms,
        # so call subsumption is not possible.
        #
        # However, subsumption through equality is still possible.
        result = False
        for cl in answers:
            # XXX: cl.body and cl.delayed empty? This might be an issue.
            if cl.head == clause.head and worlds.equivalent(cl.sentence, clause.sentence, self.kb):
                result =  True
        if self.debugger: self.debugger.note("answer_subsumed_by({}, {}) -> {}".format(clause, '{' + ', '.join("{}".format(a) for a in answers) + '}', result))
        return result

    def slg_positive(self, literal, clause, selected, mins):
        """
        [Chen et al., Figure 16, p. 183]
        """
        if selected.tag() not in self.subgoals:
            subgoal = Subgoal(selected)
            subgoal.poss.append(Waiter(literal, clause, selected))
            self.subgoals[selected.tag()] = subgoal
            dfn = self.count
            poslink = self.count
            neglink = float('inf')
            self.stack.append(Frame(subgoal, dfn, poslink, neglink))
            self.count += 1
            bmins = Mins(dfn, float('inf'))
            self.slg_subgoal(selected, bmins)
            self.update_solution(literal, selected, True, mins, bmins)
        else:
            subgoal = self.subgoals[selected.tag()]
            if not subgoal.comp:
                subgoal.poss.append(Waiter(literal, clause, selected))
                self.update_lookup(literal, selected, True, mins)
            todo = []
            def fact_in_collection(fact, collection):
                for cl in collection:
                    if cl.head == fact and not cl.body and not cl.delayed:
                        return True
                return False
            for c in subgoal.anss:
                if fact_in_collection(c.head, subgoal.anss):
                    # try to unify with already present answers, this should only
                    # fail if it leads to a contradictory world
                    resolvent = self.slg_resolve(clause, selected, Clause(c.head,[],[],c.sentence))
                    if resolvent is not None:
                        todo.append(resolvent)
                else:
                    resolvent = self.slg_factor(clause, selected, c)
                    assert resolvent is not None
                    todo.append(resolvent)
                    #todo.append(self.slg_factor(clause, selected, c))
            for c in todo:
                self.slg_newclause(literal, c, mins)
