# POS Cash Alert

Este módulo permite configurar un límite máximo de efectivo en la caja del Punto de Venta (POS) y mostrar una alerta cuando se alcance dicho límite.

## Configuración

1. Dirígete a **Punto de Venta** > **Configuración** > **Cajas POS**.
2. Selecciona la caja a la que deseas establecer un límite de efectivo.
3. En los ajustes de la caja, encontrarás un nuevo campo llamado **Límite Máximo de Efectivo**.
4. Ingresa el monto máximo de efectivo permitido para esa caja.
5. Guarda los cambios.

## Funcionamiento

- Cuando el cajero reciba pagos en efectivo, el sistema sumará el monto acumulado de efectivo en la caja.
- Si el efectivo acumulado supera el **Límite Máximo de Efectivo**, se mostrará una alerta al cajero con el mensaje:

  `"Ha alcanzado su límite de efectivo máximo por la cantidad de {monto_actual}. Favor de hacer el retiro correspondiente."`
- El cajero puede continuar operando después de cerrar la alerta.

¡Eso es todo! El sistema estará configurado para mostrar la alerta cuando se alcance el límite de efectivo.

