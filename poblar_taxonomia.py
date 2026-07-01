import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nucleo_rj.settings')
django.setup()

from intranet.models.rrhh_core import Negocio, Area, Cargo

def poblar():
    # 1. Asesores por Cliente (Negocio -> Cliente, Area -> Cartera)
    clientes_carteras = {
        "BAN BIF": ["Vigente y Dracma", "Preventiva", "Temprana", "Castigo"],
        "BBVA TARDÍAS": ["ExtraJudicial", "Judicial", "Castigo"],
        "BBVA CONTINENTAL": ["CHALLENGER", "Consumer"],
        "BBVA TEMPRANAS": ["Particulares Vencida", "Convenios", "Castigo"],
        "CAMPO": ["Campo"],
        "CAMPO BBVA": ["Campo"],
        "COMPARTAMOS BANCO": ["Vigente", "Grupal Liga A", "Castigo (Individual)"],
        "FINANCIERA EFECTIVA": ["Xperto 1 y 2", "Castigo / CASTIGO"],
        "CAJA HUANCAYO": [],
        "IBK - BPE": [],
        "VOLVO": [],
        "RJ COMPARTAMOS": ["RJ .COMPARTAMOS"],
        "RJ ADMINISTRATIVO": [],
        "Otros / No especificado": ["Judicial"]
    }

    print("--- Creando Negocios (Clientes) y Áreas (Carteras) para Asesores ---")
    for cliente_nombre, carteras in clientes_carteras.items():
        negocio, created = Negocio.objects.get_or_create(nombre=cliente_nombre)
        if created:
            print(f"Creado Negocio: {negocio.nombre}")
        
        for cartera in carteras:
            # Para evitar duplicados en Area (unique=True), prefijamos con el nombre del cliente si es muy genérico
            # O simplemente lo ponemos como "CLIENTE - Cartera"
            area_nombre = f"{cliente_nombre} - {cartera}"
            area, created_area = Area.objects.get_or_create(nombre=area_nombre)
            if created_area:
                print(f"Creada Área (Cartera): {area.nombre}")
                
            # Crear un cargo genérico de Asesor para esta área
            Cargo.objects.get_or_create(area=area, nombre="Asesor de Cobranzas")

    print("\n--- Creando Áreas y Cargos para Personal Administrativo y Supervisión ---")
    admin_data = [
        ("BANCOS", "Sin área específica", ["SUPERVISOR ESAN", "Supervisor(a) de Gestión"]),
        ("BAN BIF", "BAN BIF", ["Coordinador(a) Junior"]),
        ("BBVA TARDÍAS", "BBVA CASTIGO / BVVA CASTIGO", ["Coordinador(a) Junior", "Coordinador(a) de Gestión", "Supervisora de Gestion (BBVA Castigo)"]),
        ("BBVA TEMPRANAS", "BBVA Convenios/Delfos", ["Supervisor(a) de Gestión"]),
        ("BBVA TARDÍAS", "BBVA ExtraJudicial", ["Supervisor de Gestion"]),
        ("BBVA TARDÍAS", "BBVA JUDICIAL", ["Coordinador(a) Junior"]),
        ("BBVA TEMPRANAS", "BBVA Particulares Vencida", ["Coordinador(a) de Gestión", "Supervisor(a) de Gestión", "Supervisora (BBVA Prev. - Particulares . Vcda. Tard)"]),
        ("COMPARTAMOS BANCO", "COMPARTAMOS BANCO / RJ .COMPARTAMOS", ["Coordinador(a) de Gestión"]),
        ("FINANCIERA EFECTIVA", "Efectiva - IBK BPE", ["Supervisora de Gestion"]),
        ("FINANCIERA EFECTIVA", "FINANCIERA EFECTIVA", ["Supervisora (EFECTIVA - XPERTO - CASTIGO)"]),
        ("BBVA TEMPRANAS", "Pymes Vencida", ["JEFE DE GESTION (MAF - Vda Pymes)"]),
        ("BBVA TEMPRANAS", "Tempranas", ["SUBGERENCIA COMERCIAL"]),
        ("CAMPO", "Campo", ["Coordinador(a) de Campo", "Supervisor de Gestion de Campo - SENIOR"]),
        ("RJ ADMINISTRATIVO", "Administración General", ["Jefe de Administración", "Administrativo", "Asistente Administrativo", "Gerente General"]),
        ("RJ ADMINISTRATIVO", "Área Back Office", ["Back Office", "Supervisor(a) BACK OFFICE", "Digitadora"]),
        ("RJ ADMINISTRATIVO", "Área de Calidad y Formación", ["Jefe de Calidad y RR. HH.", "Coordinador(a) de Calidad y Formacion", "Coordinador(a) de Calidad", "Supervisor(a) de Calidad", "Asistente de Calidad y Formacion", "Asistente de Calidad"]),
        ("RJ ADMINISTRATIVO", "Área de Contabilidad y Finanzas", ["Contador", "Coordinador (a) de Contabilidad", "Asistente de Contabilidad", "Asistente Contable"]),
        ("RJ ADMINISTRATIVO", "Área Legal", ["Asesor Legal"]),
        ("RJ ADMINISTRATIVO", "Área de Mantenimiento y Logística", ["Asistente de Logística / Asistente de Logistica"]),
        ("RJ ADMINISTRATIVO", "Área de Recursos Humanos", ["Supervisora de RRHH", "Coordinador(a) de RRHH", "Asistente de RRHH", "Médico Ocupacional", "Coordinador de Capacitación"]),
        ("RJ ADMINISTRATIVO", "Área de Seguridad", ["Jefe de Seguridad", "Coordinador de Seguridad"]),
        ("RJ ADMINISTRATIVO", "Área de Tecnologías de la Información (Sistemas)", ["Supervisor Informático", "Supervisor TI", "Coordinador(a) de Sistemas", "Asistente de Sistemas", "Asistente (Monitoreo Of. San Isidro - LIMA)", "Asistente Soporte Técnico"]),
        ("RJ ADMINISTRATIVO", "Central Telefónica", ["Central Telefónica"]),
        ("RJ ADMINISTRATIVO", "Marketing", ["Asistente de Marketing"]),
        ("RJ ADMINISTRATIVO", "Mandos Medios / Operativos", ["Jefe de Productividad", "Coordinador Zonal", "Supervisor(a) Zonal", "Supervisor Junior de Gestion", "Supervisor(a) de Gestión", "Asistente de Gestión"]),
    ]

    for cliente_nombre, area_nombre, cargos in admin_data:
        # Asegurarse de que el Negocio existe
        negocio, _ = Negocio.objects.get_or_create(nombre=cliente_nombre)
        
        # Crear Área
        # Para personal de supervisión específico a un cliente, es mejor poner el prefijo si ya existe el nombre
        # o usar el nombre original si es administrativo.
        if cliente_nombre == "RJ ADMINISTRATIVO" or cliente_nombre == "BANCOS":
            final_area_nombre = area_nombre
        else:
            final_area_nombre = f"{cliente_nombre} - {area_nombre}"

        area, created_area = Area.objects.get_or_create(nombre=final_area_nombre)
        if created_area:
            print(f"Creada Área Administrativa/Supervisión: {area.nombre}")

        # Crear Cargos
        for cargo_nombre in cargos:
            cargo, created_cargo = Cargo.objects.get_or_create(area=area, nombre=cargo_nombre)
            if created_cargo:
                print(f"Creado Cargo: {cargo.nombre} (en {area.nombre})")

    print("\nProceso Completado Exitosamente.")

if __name__ == '__main__':
    poblar()
