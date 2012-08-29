from wtforms import fields

#from peewee import DateTimeField, DateField, TimeField, BaseModel, ForeignKeyField
from mongoengine.fields import DateTimeField, ReferenceField
from mongoengine.base import TopLevelDocumentMetaclass

#from wtfpeewee.orm import ModelConverter, model_form
from flask.ext.mongoengine.wtf.orm import model_fields, model_form, ModelConverter

from flask.ext.admin import form
from flask.ext.admin.model.form import InlineFormAdmin
from flask.ext.admin.model.fields import InlineModelFormField
from flask.ext.admin.model.widgets import InlineFormListWidget

#from .tools import get_primary_key

from wtforms import fields as f, validators







class InlineModelFormList(fields.FieldList):
    widget = InlineFormListWidget()

    def __init__(self, form, model, prop, **kwargs):
        self.form = form
        self.model = model
        self.prop = prop
        self._pk =  model.id #get_primary_key(model)
        print "InlineModelFormList - primary key = ", self._pk
        print dir(model.id)
        super(InlineModelFormList, self).__init__(InlineModelFormField(form, self._pk), **kwargs)

    def __call__(self, **kwargs):
        print self.form().__dict__
        return self.widget(self, template=self.form(), **kwargs)

    def get_pk(self): 
        print "get_pk called: ", self.model.id
        return self.model.id      

    def process(self, formdata, data=None):
        if not formdata:
            print "InlineModelFormList.process data = ", data
            data = self.model.objects(user=data).all()# select().where(user=data).execute()
        else:
            data = None

        return super(InlineModelFormList, self).process(formdata, data)

    def populate_obj(self, obj, name):
        pass

    def save_related(self, obj):
        print "--- save_related called"

        model_id = obj.id #getattr(obj, self._pk)

        values = self.model.select().where(user=model_id).execute()

        pk_map = dict((str(getattr(v, self._pk)), v) for v in values)

        # Handle request data
        for field in self.entries:
            field_id = field.get_pk()

            if field_id in pk_map:
                model = pk_map[field_id]

                if field.should_delete():
                    model.delete_instance(recursive=True)
                    continue
            else:
                model = self.model()

            field.populate_obj(model, None)

            # Force relation
            setattr(model, self.prop, model_id)

            model.save()


def converts(*args):
    def _inner(func):
        func._converter_for = frozenset(args)
        return func
    return _inner

class CustomModelConverter(ModelConverter):

    @converts('DateTimeField')
    def conv_DateTime(self, model, field, kwargs):
        kwargs['widget'] = form.DateTimePickerWidget()
        return f.DateTimeField(**kwargs)   


def contribute_inline(model, form_class, inline_models):
    # Contribute columns
    for p in inline_models:
        # Figure out settings
        # FIXME - not sure if works
        if isinstance(p, tuple):            
            info = InlineFormAdmin(p[0], **p[1])            
            print "----- contribute_inline: got tuple:", info
        elif isinstance(p, InlineFormAdmin):
            info = p
            print "----- contribute_inline: got InlineFormAdmin:", info
        elif isinstance(p, TopLevelDocumentMetaclass):
            info = InlineFormAdmin(p)
            print "----- contribute_inline: got TopLevelDocumentMetaclass:", info
        else:
            raise Exception('Unknown inline model admin: %s' % repr(p))
        
        # Find property from target model to current model
        reverse_field = None


        print "--- contribute_inline - model: ", model
        print "--- contribute_inline - info.model: ", info.model
        print "--- contribute_inline - iterating through info.model fields: ", info.model
        for name, field in model_fields(info.model).items():       
            if field.kwargs.has_key('model'):
                print "field with model: ", field.kwargs['model']
            #    field.to == model
                reverse_field = field
                break
        else:
            raise Exception('Cannot find reverse relation for model %s' % info.model)

        # Remove reverse property from the list
        ignore = [reverse_field.kwargs['model']._class_name]

        if info.excluded_form_columns:
            exclude = ignore + info.excluded_form_columns
        else:
            exclude = ignore

        # Create field
        converter = CustomModelConverter()
        child_form = model_form(info.model,
                            base_class=form.BaseForm,
                            only=info.form_columns,
                            exclude=exclude,
                            field_args=info.form_args,
                            #allow_pk=True,
                            converter=converter)

        print model.__dict__
        prop_name = 'fa_%s' % model.__name__

        setattr(form_class,
                prop_name,
                InlineModelFormList(child_form,
                                    info.model,
                                    reverse_field.kwargs['model']._class_name,
                                    label=info.model.__name__))

        # setattr(field.to,
        #         prop_name,
        #         property(lambda self: self.id))

    return form_class


def save_inline(form, model):
    for _, f in form._fields.iteritems():
        if f.type == 'InlineModelFormList':
            f.save_related(model)
