class QuerysetTestHelper:
    def prepare_queryset(self, queryset, context):
        for name, field in self.fields.items():
            queryset = field.prepare_queryset(queryset, context=context.get(name, None))
        return queryset
