# Notas de descubrimiento — Grupo Altamar S.A. de C.V. (ficticio) · Plataforma de datos y agente

**Fecha:** 2026-10-29 · **Wursta:** Valentina Cruz (ingeniera de datos), Ana Lucia Mendoza (líder de compromiso)
**Altamar:** Sergio Benítez (Director de TI), Paula Quintana (Directora Comercial), Jorge Lara (Contralor)

## Contexto
- Cadena de tiendas de conveniencia en el norte de México: **186 tiendas**, centro de distribución en Monterrey, oficinas en Saltillo.
- 1,400 empleados; el equipo de analítica son 6 personas que hoy consolidan reportes en hojas de cálculo.
- Fuentes: ERP de ventas y compras (base de datos SQL Server en sitio), punto de venta (archivos diarios por tienda), inventario del CEDIS (WMS) y un programa de lealtad (API REST).

## Lo que necesitan
1. **Plataforma de datos en BigQuery** con **4 flujos de ingesta**: ventas POS, ERP compras, inventario WMS y lealtad.
2. **5 tableros** en Looker Studio: ventas por tienda, margen por categoría, quiebres de inventario, lealtad, y tablero ejecutivo.
3. **Un agente de IA** (ADK / Gemini Enterprise) para gerentes de tienda: responde preguntas sobre ventas e inventario de su tienda en lenguaje natural. Complejidad media.
4. Capacitación: **4 sesiones** en vivo (analistas, gerentes regionales, administradores).
5. **Hypercare de 4 semanas**.
6. Una **zona de aterrizaje** (landing zone) en Google Cloud — hoy no tienen nada en la nube.

## Restricciones
- Contrato y entregables **en español**; facturación preferida **en pesos mexicanos** a través del socio local, o en USD si Wursta factura desde EE. UU. (el Contralor quiere ver ambos escenarios con IVA y retenciones).
- Inicio deseado: **2027-01-18**; tableros en producción antes de **2027-04-30**.
- Presupuesto aproximado: "alrededor de 4 millones de pesos".
- Prefieren **precio fijo**; entrega desde el centro nearshore de Wursta es bienvenida.

## Fuera de alcance mencionado
- Integración con el sistema de nómina.
- Aplicación móvil para gerentes (el agente se usa desde Gemini Enterprise / Chat).
- Limpieza histórica de datos anteriores a 2023.

## Preguntas abiertas
- Calidad de los archivos POS (formatos distintos por versión de caja).
- ¿Quién aprueba las respuestas del agente antes de producción?
