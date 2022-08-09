# Generated by Django 3.2.12 on 2022-08-09 14:14

from django.db import migrations

from core.models import PossibleError
from graphql_api.types.enums.enums import CommitErrorTypes


def add_type(apps, schema):
    for type in CommitErrorTypes:
        for error in type.value:
            err = PossibleError(type=type.name, code=error.value)
            err.save()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0015_commiterror_possibleerror"),
    ]

    operations = [migrations.RunPython(add_type)]
