from mongoengine import StringField
from mongoengine import LongField
from mongoengine import DictField
from mongoengine import BooleanField
from mongoengine import IntField
from mongoengine import DateTimeField
from mongoengine import Document
from mongoengine import QuerySet
from mongoengine import EmbeddedDocument
from mongoengine import EmbeddedDocumentField
from mongoengine import EmbeddedDocumentListField


class Commit(Document):
    opcode = StringField(required=True, max_length=50)
    timestamp = LongField(required=True)
    order = IntField(required=True)
    proof = StringField(max_length=150)
    data = DictField(required=True)
    address = StringField(max_length=150)

    meta = {
        "indexes": [
            "proof",
            "address"
        ]
    }


class Schedule(Document):
    opcode = StringField(required=True, max_length=50)
    timestamp = LongField(required=True)
    data = DictField(required=True)


class ClockQuerySet(QuerySet):
    def get_clock(self):
        return self.first()


class ClockModel(Document):
    time = StringField(required=True)
    meta = {'queryset_class': ClockQuerySet}


class OracleRate(Document):
    oracle = StringField(required=True, max_length=150)
    signer = StringField(required=True, max_length=150)
    signer_name = StringField(required=True, max_length=150)
    raw_rate = StringField(required=True, max_length=150)
    rate = StringField(required=True, max_length=150)
    median_rate = StringField(required=True, max_length=150)
    raw_median_rate = StringField(required=True, max_length=150)
    symbol = StringField(required=True, max_length=150)
    timestamp = StringField(required=True, max_length=150)
    time_bson = DateTimeField(required=True)
    signer_balance = StringField(required=True, max_length=150)

class ProvideRate(Document):
    oracle = StringField(required=True, max_length=150)
    signer = StringField(required=True, max_length=150)
    rate = StringField(required=True, max_length=150)

    meta = {
        "indexes": [
            "oracle",
            "signer"
        ]
    }