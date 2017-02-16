from judged import worlds


class Action:
    def __init__(self, source=None):
        self.source = source

    def perform(self, context):
        raise NotImplementedError


class AssertAction(Action):
    def __init__(self, clause, *, source=None):
        super().__init__(source)
        self.clause = clause

    def perform(self, context):
        context.knowledge.assert_clause(self.clause)

    def __str__(self):
        return "assert {}".format(self.clause)


class RetractAction(Action):
    def __init__(self, clause, *, source=None):
        super().__init__(source)
        self.clause = clause

    def perform(self, context):
        context.knowledge.retract_clause(clause)

    def __str__(self):
        return "retract {}".format(self.clause)


class QueryAction(Action):
    def __init__(self, clause, *, source=None):
        super().__init__(source)
        if len(clause) > 0:
            raise judged.JudgedError('Cannot query for a clause (only literals can be queried on).')
        if clause.sentence != worlds.Top():
            raise judged.JudgedError('Cannot perform a query with a descriptive sentence.')

        self.clause = clause

    def perform(self, context):
        literal = self.clause.head
        result = context.ask(literal)
        return result

    def __str__(self):
        return "query {}".format(self.clause)


class AnnotateProbabilityAction(Action):
    def __init__(self, label, probability, *, source=None):
        super().__init__(source)
        self.label = label
        self.probability = probability

    def perform(self, context):
        context.add_probability(self.label.partitioning, self.label.part, self.probability)

    def __str__(self):
        return "annotate p({}) = {}".format(self.label, self.probability)


class AnnotateDistributionAction(Action):
    def __init__(self, partitioning, distribution, *, source=None):
        super().__init__(source)
        self.partitioning = partitioning
        self.distribution = distribution

    def perform(self, context):
        # determine all present parts
        parts = context.knowledge.parts(self.partitioning)

        if parts:
            for part in parts:
                context.add_probability(self.partitioning, part, 1/len(parts))

    def __str__(self):
        return "annotate p({}) with {} distribution".format(self.partitioning, self.distribution)


class UseModuleAction(Action):
    def __init__(self, module, config={}, *, source=None):
        super().__init__(source)
        self.module = module
        self.config = config

    def perform(self, context):
        ext = extensions.known_extensions.get(module)
        if ext is None:
            raise extensions.ExtensionError("Module '{}' not found.".format(module))

        context.use_extension(ext, config)
        return ext

    def __str__(self):
        return "use module '{}'".format(self.module) + ("with arguments {}".format(self.config) if self.config else '')


class UsePredicateAction(Action):
    def __init__(self, module, predicate, alias=None, *, source=None):
        super().__init__(source)
        self.module = module
        self.predicate = predicate
        self.alias = alias

    def perform(self, context):
        ext = context.extensions.get(self.module)
        if not ext:
            ext = UseModuleAction(self.module, {}).perform(context)
        ext.register_predicate(context, predicate, alias)

    def __str__(self):
        return "use predicate '{}' from module '{}'".format(self.predicate, self.module) + (" aliased as '{}'".format(self.alias) if self.alias else '')
