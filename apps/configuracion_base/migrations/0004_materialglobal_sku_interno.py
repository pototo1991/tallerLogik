# Generated & manually edited for data migration of sku_interno

from django.db import migrations, models


def generar_sku_internos(apps, schema_editor):
    """
    Rellena sku_interno para todos los registros existentes de MaterialGlobal.
    Formato: TL-000001, TL-000002, ...
    """
    MaterialGlobal = apps.get_model('configuracion_base', 'MaterialGlobal')
    for idx, material in enumerate(MaterialGlobal.objects.order_by('nombre'), start=1):
        material.sku_interno = f'TL-{idx:06d}'
        material.save(update_fields=['sku_interno'])


class Migration(migrations.Migration):

    dependencies = [
        ('configuracion_base', '0003_materialglobal_material_actualizacion_automatica_and_more'),
    ]

    operations = [
        # Paso 1: Agregar el campo SIN restriccion unica (nullable temporalmente)
        migrations.AddField(
            model_name='materialglobal',
            name='sku_interno',
            field=models.CharField(
                db_index=False,
                editable=False,
                max_length=20,
                null=True,
                blank=True,
                verbose_name='SKU Interno'
            ),
        ),

        # Paso 2: Rellenar todos los registros existentes con SKUs unicos
        migrations.RunPython(
            generar_sku_internos,
            reverse_code=migrations.RunPython.noop
        ),

        # Paso 3: Aplicar la restriccion unica ahora que todos tienen valor
        migrations.AlterField(
            model_name='materialglobal',
            name='sku_interno',
            field=models.CharField(
                db_index=True,
                editable=False,
                max_length=20,
                unique=True,
                verbose_name='SKU Interno'
            ),
        ),

        # Paso 4: Actualizar sku_proveedor (ampliar max_length a 150)
        migrations.AlterField(
            model_name='materialglobal',
            name='sku_proveedor',
            field=models.CharField(
                db_index=True,
                max_length=150,
                unique=True,
                verbose_name='SKU Proveedor'
            ),
        ),
    ]
