def crear_estado_kanban(row):
    aprobacion = str(row.get('Estado Aprobación', '')).strip()
    produccion = str(row.get('Estado Producción', '')).strip()
    
    # PRIMERO: Verificar Estado Aprobación
    if aprobacion == 'Pendiente':
        return 'Pendiente Aprobación'
    
    # SEGUNDO: Si está Aprobado, verificar Estado Producción
    elif aprobacion == 'Aprobado':
        if produccion == 'En Espera':
            return 'En Espera'
        elif produccion == 'En Proceso':
            return 'En Proceso'
        elif produccion == 'Completado':
            return 'Completado'
        elif produccion == 'Entregado':
            return 'Entregado'
        else:
            return 'En Espera'  # Default si está aprobado
    
    return 'Pendiente Aprobación'
