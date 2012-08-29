from flask import flash

from flask.ext.admin import form
from flask.ext.admin.babel import gettext, ngettext, lazy_gettext
from flask.ext.admin.model import BaseModelView

#from peewee import PrimaryKeyField, ForeignKeyField, Field, CharField, TextField
# replaced! from wtfpeewee.orm import model_form               

from flask.ext.admin.actions import action
from flask.ext.admin.contrib.mongoenginemodel import filters
from .form import CustomModelConverter, contribute_inline, save_inline
from .form import contribute_inline, save_inline

from mongoengine import Q


# === my 
#.form.CustomModelConverter -> orm.ModelConverter
from flask.ext.mongoengine.wtf.orm import model_fields, model_form, ModelConverter


class ModelView(BaseModelView):
    column_filters = None
    """
        Collection of the column filters.

        Can contain either field names or instances of :class:`flask.ext.admin.contrib.sqlamodel.filters.BaseFilter` classes.

        For example::

            class MyModelView(BaseModelView):
                column_filters = ('user', 'email')

        or::

            class MyModelView(BaseModelView):
                column_filters = (BooleanEqualFilter(User.name, 'Name'))
    """

    filter_converter = filters.FilterConverter()
    """
        Field to filter converter.

        Override this attribute to use non-default converter.
    """

    fast_mass_delete = False
    """
        If set to `False` and user deletes more than one model using actions,
        all models will be read from the database and then deleted one by one
        giving SQLAlchemy chance to manually cleanup any dependencies (many-to-many
        relationships, etc).

        If set to True, will run DELETE statement which is somewhat faster, but
        might leave corrupted data if you forget to configure DELETE CASCADE
        for your model.
    """

    inline_models = None
    """
        Inline related-model editing for models with parent to child relation.

        Accept enumerable with one of the values:

        1. Child model class

            class MyModelView(ModelView):
                inline_models = (Post,)

        2. Child model class and additional options

            class MyModelView(ModelView):
                inline_models = [(Post, dict(form_columns=['title']))]

        3. Django-like ``InlineFormAdmin`` class instance

            class MyInlineForm(InlineFormAdmin):
                forum_columns = ('title', 'date')

            class MyModelView(ModelView):
                inline_models = (MyInlineForm,)
    """

    def __init__(self, model, name=None,
                 category=None, endpoint=None, url=None):
        self._search_fields = []

        super(ModelView, self).__init__(model, name, category, endpoint, url)
        # FIXME: primary keys
        self._primary_key = self.model.id

    # ok
    def _get_model_fields(self, model=None):
        """Returns WTForms field list"""
        if model is None:
            model = self.model

        return model_fields(model).items()

    # FIXME: primary keys
    def get_pk_value(self, model): 
        print "============ get_pk_value: ", model.id       
        return model.id

    def scaffold_list_columns(self):
        """returns list of columns names"""
        columns = []

        for n, f in self._get_model_fields():
            # Filter by name
            if (self.excluded_list_columns and
                n in self.excluded_list_columns):
                continue

            # Verify type
            field_class = type(f)

            # if field_class == ForeignKeyField:    # FIXME
            #     columns.append(n)
            # elif field_class != PrimaryKeyField:
            #     columns.append(n)
            columns.append(n)                       # fixme-stub
        return columns

    def scaffold_sortable_columns(self):
        columns = dict()

        for n, f in self._get_model_fields():
            columns[n] = f
            #if type(f) != PrimaryKeyField:  # FIXME
            #    columns[n] = f

        return columns

    def init_search(self):
        if self.searchable_columns:
            for p in self.searchable_columns:
                if isinstance(p, basestring):
                    p = getattr(self.model, p)

                field_type = type(p)

                # Check type
                if (field_type != CharField and
                    field_type != TextField):
                        raise Exception('Can only search on text columns. ' +
                                        'Failed to setup search for "%s"' % p)

                self._search_fields.append(p)

        return bool(self._search_fields)

    # ok
    def scaffold_filters(self, name):
        """returns list of <class 'flask_admin.contrib.mongoengine.filters.xxx'>"""
        if isinstance(name, basestring):
            attr = getattr(self.model, name, None)
        else:
            attr = name

        if attr is None:
            raise Exception('Failed to find field for filter: %s' % name)

        # Check if field is in different model
        # attr - <mongoengine.fields.StringField object at 0x015E2930>
        # attr.model = attr.owner_document
        print "attr.name = ", attr.name
        if attr.owner_document != self.model:
            visible_name = '%s / %s' % (self.get_column_name(attr.owner_document.__name__),
                                        self.get_column_name(attr.name))
        else:
            if not isinstance(name, basestring):
                visible_name = self.get_column_name(attr.name)
            else:
                visible_name = self.get_column_name(name)
        print "visible_name = ", visible_name

        type_name = type(attr).__name__
        print "type_name, attr, visible_name: ", type_name, attr, visible_name
        print "call filter_converter.convert"
        flt = self.filter_converter.convert(type_name,
                                            attr,
                                            visible_name)
        print flt
        return flt

    def is_valid_filter(self, filter):
        return isinstance(filter, filters.BasePeeweeFilter)

    def scaffold_form(self):
        form_class = model_form(self.model,
                        base_class=form.BaseForm,
                        only=self.form_columns,
                        exclude=self.excluded_form_columns,
                        field_args=self.form_args,
                        converter=CustomModelConverter())

        if self.inline_models:
            raise NotImplementedError("Inline forms not implemented")
            #form_class = contribute_inline(self.model, form_class, self.inline_models)

        return form_class

    def _handle_join(self, query, field, joins):
        if field.model != self.model:
            model_name = field.model.__name__

            if model_name not in joins:
                query = query.join(field.model)
                joins.add(model_name)

        return query

    def get_list(self, page, sort_column, sort_desc, search, filters,
                 execute=True):
        """
            Return list of models from the data source with applied pagination
            and sorting.

            Must be implemented in child class.

            :param page:
                Page number, 0 based. Can be set to None if it is first page.
            :param sort_field:
                Sort column name or None.
            :param sort_desc:
                If set to True, sorting is in descending order.
            :param search:
                Search query
            :param filters:
                List of filter tuples. First value in a tuple is a search
                index, second value is a search value.
        """    
        print "get_list call"

        # joins = set()

        # # Search
        # if self._search_supported and search:
        #     terms = search.split(' ')

        #     for term in terms:
        #         if not term:
        #             continue

        #         stmt = None
        #         for field in self._search_fields:
        #             query = self._handle_join(query, field, joins)

        #             q = field ** term

        #             if stmt is None:
        #                 stmt = q
        #             else:
        #                 stmt |= q

        #         query = query.where(stmt)

        # Filters
        # 
        if self._filters:
            flash('Not implemented: filters in /mongoenginemodel/filters.py: Common filters', 'error')
            conditions = []
            for flt, value in filters:        
                conditions.append(self._filters[flt].apply(None, value))
            import ast
            str_query = "{%s}" % ', '.join(conditions)          
            mongo_query = ast.literal_eval(str_query)            
        else:
            mongo_query = {}

       
        result = self.model.objects(__raw__=mongo_query).all()
        # Get count
        count = len(result)

        # # Apply sorting
        if sort_column is not None:
            #raise NotImplementedError
            flash('Not implemented: sorting in /mongoenginemodel/views.py: get_list()', 'error')
        #     sort_field = self._sortable_columns[sort_column]

        #     if isinstance(sort_field, basestring):
        #         query = query.order_by((sort_field, sort_desc and 'desc' or 'asc'))
        #     elif isinstance(sort_field, Field):
        #         if sort_field.model != self.model:
        #             query = self._handle_join(query, sort_field, joins)

        #             query = query.order_by((sort_field.model, sort_field.name, sort_desc and 'desc' or 'asc'))
        #         else:
        #             query = query.order_by((sort_column, sort_desc and 'desc' or 'asc'))

        # # Pagination
        # if page is not None:
        #     query = query.offset(page * self.page_size)

        # query = query.limit(self.page_size)

        # if execute:
        #     query = query.execute()
        
        #print query
        return count, result

    def get_one(self, id):
        return self.model.objects(id=id).first()

    def create_model(self, form):
        try:
            model = self.model()
            form.populate_obj(model)
            model.save()

            # For peewee have to save inline forms after model was saved
            save_inline(form, model)

            return True
        except Exception, ex:
            flash(gettext('Failed to create model. %(error)s', error=str(ex)), 'error')
            return False

    def update_model(self, form, model):
        print "---update_model called"
        try:
            form.populate_obj(model)
            model.save()

            # For peewee have to save inline forms after model was saved
            save_inline(form, model)

            return True
        except Exception, ex:
            flash(gettext('Failed to update model. %(error)s', error=str(ex)), 'error')
            return False

    def delete_model(self, model):
        try:
            print "--- view.py:delete_model // FIXME: 'safe' flag is always true //", model.id
            model.delete(safe=True)
            return True
        except Exception, ex:
            flash(gettext('Failed to delete model. %(error)s', error=str(ex)), 'error')
            return False

    # Default model actions
    def is_action_allowed(self, name):
        # Check delete action permission
        if name == 'delete' and not self.can_delete:
            return False

        return super(ModelView, self).is_action_allowed(name)

    @action('delete',
            lazy_gettext('Delete'),
            lazy_gettext('Are you sure you want to delete selected models?'))
    def action_delete(self, ids):
        try:
            documents = self.model.objects(id__in=ids)
            count = documents.count()
            documents.delete()
            
            flash(ngettext('Record was successfully deleted.',
                           '%(count)s records were sucessfully deleted.',
                           count,
                           count=count))
        except Exception, ex:
            flash(gettext('Failed to delete records. %(error)s', error=str(ex)), 'error')
