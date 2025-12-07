import rdflib


class ExtendedGraph(rdflib.ConjunctiveGraph):
    """
    ConjunctiveGraph must be used as a BaseClass (instead of Graph)
    to serialize graph into some .rdf formats like trix or n-quads.
    """

    def __init__(self, *args, ordered=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.ordered = ordered

    def subjects(self, predicate=None, object=None):
        """
        A generator of subjects with the given predicate and object.

        Method is used by serializers.
        By default subjects are unordered (python's set is used internally),
        so each time serializer can give document rendered in different order.

        If `ordered` attribute is set during initialization,
        generated subjects are to be sorted in the following manner:
            - first `BNode`s ordered alphabetically
            - then `URIRef`s ordered alphabetically
        """
        result = super().subjects(predicate=predicate, object=object)
        if predicate is None and object is None and self.ordered:
            result = sorted(result)
        return result

    def predicate_objects(self, subject=None):
        """
        A generator of (predicate, object) tuples for the given subject

        Method is used by serializers.
        By default subjects are unordered (python's set is used internally),
        so each time serializer can give document rendered in different order.

        If `ordered` attribute is set during initialization,
        generated predicates are to be sorted alphabetically:
        """
        result = super().predicate_objects(subject=subject)
        if self.ordered:
            result = sorted(result)
        return result
