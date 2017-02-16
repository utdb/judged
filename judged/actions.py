from judged import worlds

class Action:
    def perform(self, context):
        raise NotImplementedError


class AssertAction:
    def __init__(self, clause):
        self.clause = clause

    def perform(self, context):
        context.knowledge.assert_clause(self.clause)


class RetractAction:
    def __init__(self, clause):
        self.clause = clause

    def perform(self, context):
        context.knowledge.retract_clause(clause)


class QueryAction:
    def __init__(self, clause):
        if len(clause) > 0:
            raise judged.JudgedError('Cannot query for a clause (only literals can be queried on).')
        if clause.sentence != worlds.Top():
            raise judged.JudgedError('Cannot perform a query with a descriptive sentence.')

        self.clause = clause

    def perform(self, context):
        literal = self.clause.head
        result = context.ask(literal)
        return result


class AnnotateProbabilityAction:
    def __init__(self, partitioning, part, probability):
        self.partitioning = partitioning
        self.part = part
        self.probability = probability

    def perform(self, context):
        context.add_probability(self.partitioning, self.part, self.probability)


class AnnotateDistributionAction:
    def __init__(self, partitioning, distribution):
        self.partitioning = partitioning
        self.distribution = distribution

    def perform(self, context):
        # determine all present parts
        parts = context.knowledge.parts(self.partitioning)

        if parts:
            for part in parts:
                context.add_probability(self.partitioning, part, 1/len(parts))


class UseModuleAction:
    def __init__(self, module, config={}):
        self.module = module
        self.config = config

    def perform(self, context):
        ext = extensions.known_extensions.get(module)
        if ext is None:
            raise extensions.ExtensionError("Module '{}' not found.".format(module))

        context.use_extension(ext, config)
        return ext


class UsePredicateAction:
    def __init__(self, module, predicate, alias=None):
        self.module = module
        self.predicate = predicate
        self.alias = alias

    def perform(self, context):
        ext = context.extensions.get(self.module)
        if not ext:
            ext = UseModuleAction(self.module, {}).perform(context)
        ext.register_predicate(context, predicate, alias)
