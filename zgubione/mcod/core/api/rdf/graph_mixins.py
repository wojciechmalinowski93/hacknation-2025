from django.db.models import Max, Model

from mcod.core.api.rdf.namespaces import NAMESPACES


class SparqlGraphCatalogModifiedMixin:

    def _prepare_catalog_modified_query(self, instance):
        catalog = self.get_rdf_class_for_catalog()()
        catalog_subject = catalog.get_subject({})

        if isinstance(instance, Model):
            modified = instance.modified
        else:
            modified = instance.aggregate(max_modified=Max("modified"))["max_modified"]
        modified_triple = catalog.make_triple(subject=catalog_subject, object_value=modified, field_name="modified")
        return {"dct": NAMESPACES["dct"]}, modified_triple, catalog_subject

    def update_catalog_modified(self, instance):
        ns, modified_triple, subject = self._prepare_catalog_modified_query(instance)
        catalog_node = f"{modified_triple[0].n3()} {modified_triple[1].n3()} {modified_triple[2].n3()} . "
        delete_q = self._get_delete_triple_filter_query(modified_triple[0], modified_triple[1])
        create_q = self._get_create_query({subject: catalog_node})
        update_query = f"{delete_q}; {create_q}"
        return update_query, ns
