from peewee import *

# pragmas on: the on_delete has a real effect on the SQLite db
db = SqliteDatabase('website_monitor.db', pragmas=(('foreign_keys', 'on'),))


class Website(Model):

    url = CharField(default="")
    check_interval = IntegerField(default=10)
    display = BooleanField(default=True)

    class Meta:
        database = db


class Check(Model):

    website = ForeignKeyField(Website, related_name="checks", on_delete='CASCADE')
    date = TimestampField()
    full_resp_time = FloatField()  # in seconds
    resp_time = FloatField()  # in seconds
    status_code = SmallIntegerField()

    class Meta:
        database = db


class Alert(Model):

    website = ForeignKeyField(Website, related_name="alerts", on_delete='CASCADE')
    date = TimestampField()
    availability = SmallIntegerField()

    class Meta:
        database = db
