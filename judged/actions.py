from judged import worlds
from judged import JudgedError
from judged import extensions


class Action:
    def __init__(self, source=None):
        self.source = source

    def perform(self, context, reporter=None):
        raise NotImplementedError

    def substitute(self, env):
        return self


class AssertAction(Action):
    def __init__(self, clause, *, source=None):
        super().__init__(source)
        self.clause = clause

    def perform(self, context, reporter=None):
        if reporter is not None:
            reporter.perform(self)

        context.knowledge.assert_clause(self.clause)

    def __str__(self):
        return "assert {}".format(self.clause)

    def substitute(self, env):
        cls = type(self)
        return cls(self.clause.subst(env), source=self.source)


class RetractAction(Action):
    def __init__(self, clause, *, source=None):
        super().__init__(source)
        self.clause = clause

    def perform(self, context, reporter=None):
        if reporter is not None:
            reporter.perform(self)

        context.knowledge.retract_clause(self.clause)

    def __str__(self):
        return "retract {}".format(self.clause)

    def substitute(self, env):
        cls = type(self)
        return cls(self.clause.subst(env), source=self.source)


class QueryAction(Action):
    def __init__(self, clause, *, source=None):
        super().__init__(source)
        if len(clause) > 0:
            raise JudgedError('Cannot query for a clause (only literals can be queried on).')
        if clause.sentence != worlds.Top():
            raise JudgedError('Cannot perform a query with a descriptive sentence.')

        self.clause = clause

    def perform(self, context, reporter=None):
        if reporter is not None:
            reporter.perform(self)

        literal = self.clause.head
        result = context.ask(literal)

        if reporter is not None:
            reporter.result(result)

        return result

    def __str__(self):
        return "query {}".format(self.clause)

    def substitute(self, env):
        cls = type(self)
        return cls(self.clause.subst(env), source=self.source)


class AnnotateProbabilityAction(Action):
    def __init__(self, label, probability, *, source=None):
        super().__init__(source)
        self.label = label
        self.probability = probability

    def perform(self, context, reporter=None):
        if reporter is not None:
            reporter.perform(self)

        context.add_probability(self.label.partitioning, self.label.part, self.probability)

    def __str__(self):
        return "annotate p({}) = {}".format(self.label, self.probability)

    def substitute(self, env):
        cls = type(self)
        return cls(self.label.subst(env), self.probability, source=self.source)


class AnnotateDistributionAction(Action):
    def __init__(self, partitioning, distribution, *, source=None):
        super().__init__(source)
        self.partitioning = partitioning
        self.distribution = distribution

    def perform(self, context, reporter=None):
        if reporter is not None:
            reporter.perform(self)

        # determine all present parts
        parts = context.knowledge.parts(self.partitioning)

        if parts:
            for part in parts:
                context.add_probability(self.partitioning, part, 1/len(parts))

    def __str__(self):
        return "annotate p({}) with {} distribution".format(self.partitioning, self.distribution)

    def substitute(self, env):
        cls = type(self)
        return cls(self.partitioning.subst(env), self.distribution, source=self.source)


class UseModuleAction(Action):
    def __init__(self, module, config={}, *, source=None):
        super().__init__(source)
        self.module = module
        self.config = config

    def perform(self, context, reporter=None):
        if reporter is not None:
            reporter.perform(self)

        ext = extensions.known_extensions.get(self.module)
        if ext is None:
            raise extensions.ExtensionError("Module '{}' not found.".format(self.module))

        context.use_extension(ext, self.config)
        return ext

    def __str__(self):
        return "use module '{}'".format(self.module) + ("with arguments {}".format(self.config) if self.config else '')


class UsePredicateAction(Action):
    def __init__(self, module, predicate, alias=None, *, source=None):
        super().__init__(source)
        self.module = module
        self.predicate = predicate
        self.alias = alias

    def perform(self, context, reporter=None):
        if reporter is not None:
            reporter.perform(self)

        ext = context.extensions.get(self.module)
        if not ext:
            ext = UseModuleAction(self.module, {}).perform(context)
        ext.register_predicate(context, self.predicate, self.alias)

    def __str__(self):
        return "use predicate '{}' from module '{}'".format(self.predicate, self.module) + (" aliased as '{}'".format(self.alias) if self.alias else '')


class CompoundAction(Action):
    def __init__(self, children, *, source=None):
        super().__init__(source)
        self.children = children

    def perform(self, context, reporter=None):
        if reporter is not None:
            reporter.perform(self)
            reporter.enter(self)

        # the last result from the compound will be the compound's result
        last_result = None
        for action in self.children:
            last_result = action.perform(context, reporter)
        if reporter is not None:
            reporter.exit()
        # return the last result for use (e.g. a query at the end or such)
        return last_result

    def __str__(self):
        return "compound of {{{}}}".format(', '.join("{}".format(c) for c in self.children))

    def substitute(self, env):
        cls = type(self)
        return cls([c.substitute(env) for c in self.children], source=self.source)

    def __getitem__(self, selector):
        return self.children[selector]

    def __iter__(self):
        return iter(self.children)


class GeneratorAction(Action):
    def __init__(self, children, query_clause, *, source=None):
        super().__init__(source)
        self.children = children
        if len(query_clause) > 0:
            raise JudgedError('Generator query clause must be a literal')
        if query_clause.sentence != worlds.Top():
            raise JudgedError('Cannot perform a query with a descriptive sentence.')
        self.query_clause = query_clause

    def perform(self, context, reporter=None):
        if reporter is not None:
            reporter.perform(self)

        result = context.ask(self.query_clause.head)

        # Skip any non-exact results
        if result.notes and result.notes.get('iterations') != 1:
            return

        for answer in result.answers:
            # skip any non-guaranteed results
            if answer.probability is not None and answer.probability != 1.0:
                continue
            if answer.clause.sentence != worlds.Top():
                continue

            # get the substitution environment for the answer
            env = self.query_clause.head.unify(answer.clause.head)
            if reporter is not None:
                reporter.enter(self)
            for action in [c.substitute(env) for c in self.children]:
                action.perform(context, reporter)
            if reporter is not None:
                reporter.exit()

    def __str__(self):
        return "generate for {{{}}} based on {}".format(', '.join("{}".format(c) for c in self.children), self.query_clause)

    def substitute(self, env):
        cls = type(self)
        return cls([c.substitute(env) for c in self.children], self.query_clause.subst(env), source=self.source)
