from flask.ext.admin.babel import gettext

from flask.ext.admin.model import filters
import re


class BasePeeweeFilter(filters.BaseFilter):
    """
        Base SQLAlchemy filter.
    """
    def __init__(self, column, name, options=None, data_type=None):
        """
            Constructor.

            :param column:
                Model field
            :param name:
                Display name
            :param options:
                Fixed set of options
            :param data_type:
                Client data type
        """
        print "BasePeeweeFilter.__init__"
        super(BasePeeweeFilter, self).__init__(name, options, data_type)
        self.column = column


# Common filters
class FilterEqual(BasePeeweeFilter):
    def apply(self, query, value):
        return '"%s": "%s"' % (self.column.name, value)

    def operation(self):
        return gettext('equals')


class FilterNotEqual(BasePeeweeFilter):
    def apply(self, query, value):
        return '"%s": {"$ne": "%s"}' % (self.column.name, value)

    def operation(self):
        return gettext('not equal')


class FilterLike(BasePeeweeFilter):
    def apply(self, query, value):
        #return query.filter(self.column ** value)
        raise NotImplemented

    def operation(self):
        return gettext('contains')


class FilterNotLike(BasePeeweeFilter):
    def apply(self, query, value):
        #return query.filter(~(self.column ** value))
        raise NotImplemented

    def operation(self):
        return gettext('not contains')


class FilterGreater(BasePeeweeFilter):
    def apply(self, query, value):
        return '"%s": {"$gt": "%s"}' % (self.column.name, value)

    def operation(self):
        return gettext('greater than')


class FilterSmaller(BasePeeweeFilter):
    def apply(self, query, value):
        return '"%s": {"$lt": "%s"}' % (self.column.name, value)        

    def operation(self):
        return gettext('smaller than')


# Customized type filters
class BooleanEqualFilter(FilterEqual, filters.BaseBooleanFilter):
    pass


class BooleanNotEqualFilter(FilterNotEqual, filters.BaseBooleanFilter):
    pass


# Base peewee filter field converter
class FilterConverter(filters.BaseFilterConverter):
    strings = (FilterEqual, FilterNotEqual, FilterLike, FilterNotLike)
    numeric = (FilterEqual, FilterNotEqual, FilterGreater, FilterSmaller)

    def convert(self, type_name, column, name):
        print "FilterConverter.convert called:"
        print type_name, column, name        
        if type_name in self.converters:
            return self.converters[type_name](column, name)

        return None

    @filters.convert('StringField', 'StringField')
    def conv_string(self, column, name):
        return [f(column, name) for f in self.strings]

    @filters.convert('BooleanField')
    def conv_bool(self, column, name):
        return [BooleanEqualFilter(column, name),
                BooleanNotEqualFilter(column, name)]

    @filters.convert('IntegerField', 'DecimalField', 'FloatField')
    def conv_int(self, column, name):
        return [f(column, name) for f in self.numeric]

    @filters.convert('DateField')
    def conv_date(self, column, name):
        return [f(column, name, data_type='datepicker') for f in self.numeric]

    @filters.convert('DateTimeField')
    def conv_datetime(self, column, name):
        return [f(column, name, data_type='datetimepicker')
                for f in self.numeric]
