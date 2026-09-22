from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inspections', '0002_alter_inspection5s_codigo_carro_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='inspection5s',
            name='firma_auditor_base64',
        ),
        migrations.RemoveField(
            model_name='inspection5s',
            name='firma_responsable_base64',
        ),
    ]