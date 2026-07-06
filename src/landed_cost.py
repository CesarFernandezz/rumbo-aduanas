def calcular_landed_cost(fob, flete, seguro, arancel_pct, tasa_pct, iva_pct, gastos_locales):
    """
    Calcula matemáticamente el costo puesto en destino (Landed Cost)
    y desglosa cada componente impositivo y logístico.
    """
    # 1. Base Imponible (CIF)
    cif = fob + flete + seguro
    
    # 2. Impuestos Aduaneros
    monto_arancel = cif * (arancel_pct / 100.0)
    monto_tasa = cif * (tasa_pct / 100.0)
    
    # Base imponible para el IVA según legislación aduanera
    base_iva = cif + monto_arancel + monto_tasa
    monto_iva = base_iva * (iva_pct / 100.0)
    
    total_impuestos = monto_arancel + monto_tasa + monto_iva
    
    # 3. Costo Total Puesto en Destino
    landed_cost_total = cif + total_impuestos + gastos_locales
    
    # 4. Indicadores de Gestión
    # Factor de importación: Cuántas veces se multiplicó el costo FOB original
    factor_importacion = landed_cost_total / fob if fob > 0 else 0
    porcentaje_incremento = ((landed_cost_total - fob) / fob) * 100 if fob > 0 else 0
    
    return {
        "cif": cif,
        "arancel": monto_arancel,
        "tasa_aduana": monto_tasa,
        "iva": monto_iva,
        "total_impuestos": total_impuestos,
        "landed_cost": landed_cost_total,
        "factor": factor_importacion,
        "incremento_pct": porcentaje_incremento
    }